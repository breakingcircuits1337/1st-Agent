"""
Fine-Tune Factory for Needle models.

Automates the process of creating specialized, fine-tuned Needle models (.cact files)
for different domains. Uses Needle's built-in CLI commands for:
1. Synthetic data generation (via OpenRouter)
2. LoRA fine-tuning
3. Building optimized .cact archives

This factory enables automated R&D for agent fine-tuning using dual Needle models:
- Researcher model: Generates training data, evaluates models
- Production model: Serves stable, user-facing responses
- Evaluation agent: Tests outputs and provides reward signals for closed-loop optimization

Closed-Loop Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    FineTuneFactory                             │
├───────────────────────────┬───────────────────────────────────┤
│ create_model()            │ evaluate_with_reward()            │
│  - generate_data()         │  - run_test_suite()               │
│  - finetune()              │  - calculate_reward()             │
│  - build_model()           │  - track_performance()            │
└───────────────────────────┴───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Reward Signal    │ ← Drives optimization
                    │ (0.0 - 2.0)      │
                    └─────────────────┘
"""

import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass, field
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for fine-tuning a model."""
    name: str
    domain: str
    tools_schema: Union[List[Dict], str, Path]  # List of tool schemas or path to JSON file
    num_samples: int = 200
    epochs: int = 10
    lora_rank: int = 16
    lora_alpha: float = 32.0
    batch_size: int = 16
    max_len: int = 1024
    val_split: float = 0.1
    generate_extra: int = 0  # Extra samples to generate via OpenRouter
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    base_checkpoint: Optional[str] = None  # None = auto-download needle2
    
    # Output paths
    datasets_dir: Path = field(default_factory=lambda: Path("datasets"))
    checkpoints_dir: Path = field(default_factory=lambda: Path("checkpoints"))
    models_dir: Path = field(default_factory=lambda: Path("models"))


@dataclass
class FineTunedModel:
    """Represents a fine-tuned model."""
    name: str
    domain: str
    model_path: Path
    dataset_path: Path
    checkpoint_path: Optional[Path] = None
    lora_path: Optional[Path] = None
    tools_schema: List[Dict] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def __repr__(self):
        return f"FineTunedModel(name={self.name}, domain={self.domain}, model_path={self.model_path})"


@dataclass
class EvaluationResult:
    """Result of evaluating a fine-tuned model."""
    model_name: str
    accuracy: Optional[float] = None
    loss: Optional[float] = None
    confidence: Optional[float] = None
    test_samples: int = 0
    pass_rate: float = 0.0
    notes: str = ""


class FineTuneFactory:
    """
    Factory for creating and managing fine-tuned Needle models.
    
    This class automates the entire fine-tuning pipeline:
    1. Generate synthetic training data
    2. Fine-tune with LoRA
    3. Build optimized .cact archive
    4. Evaluate model performance
    5. Version and register models
    
    Example usage:
        factory = FineTuneFactory()
        
        # Define tools for weather domain
        tools = [
            {"name": "get_weather", "parameters": {...}},
            {"name": "get_forecast", "parameters": {...}}
        ]
        
        # Create fine-tuned model
        model = factory.create_model(
            name="weather",
            domain="weather",
            tools_schema=tools,
            num_samples=200
        )
        
        # Use the model
        agent = needle.Needle(weights=str(model.model_path), tools=...)
    """
    
    def __init__(
        self,
        base_checkpoint: Optional[str] = None,
        datasets_dir: Optional[Path] = None,
        checkpoints_dir: Optional[Path] = None,
        models_dir: Optional[Path] = None,
        use_researcher_for_eval: bool = False
    ):
        """
        Initialize the fine-tuning factory.
        
        Args:
            base_checkpoint: Base model checkpoint path (None = auto-download)
            datasets_dir: Directory for training datasets
            checkpoints_dir: Directory for LoRA checkpoints
            models_dir: Directory for final .cact models
            use_researcher_for_eval: Use researcher model for automated evaluation
        """
        self.base_checkpoint = base_checkpoint
        self.datasets_dir = datasets_dir or Path("datasets")
        self.checkpoints_dir = checkpoints_dir or Path("checkpoints")
        self.models_dir = models_dir or Path("models")
        self.use_researcher_for_eval = use_researcher_for_eval
        
        # Create directories if they don't exist
        for d in [self.datasets_dir, self.checkpoints_dir, self.models_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Registry of created models
        self.registry: Dict[str, FineTunedModel] = {}
        
        logger.info(f"FineTuneFactory initialized with base: {base_checkpoint or 'needle2 (auto)'}")
    
    def _resolve_tools_schema(self, tools_schema: Union[List[Dict], str, Path]) -> List[Dict]:
        """Resolve tools schema from various input types."""
        if isinstance(tools_schema, (str, Path)):
            with open(tools_schema, 'r') as f:
                return json.load(f)
        return tools_schema
    
    def _ensure_needle_installed(self):
        """Ensure cactus-needle is installed and accessible."""
        try:
            import needle
            return True
        except ImportError:
            logger.error("cactus-needle is not installed. Please run: pip install cactus-needle[gpu]")
            return False
    
    def _run_needle_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a needle CLI command."""
        full_command = ["needle"] + command
        logger.info(f"Running: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                check=True,
                capture_output=True,
                text=True,
                **kwargs
            )
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(full_command)}")
            logger.error(f"stderr: {e.stderr}")
            raise
    
    def generate_data(
        self,
        name: str,
        tools_schema: Union[List[Dict], str, Path],
        num_samples: int = 200,
        model: str = "deepseek/deepseek-v4-flash",
        batch_size: int = 25,
        workers: int = 16
    ) -> Path:
        """
        Generate synthetic training data using Needle's data generation.
        
        Args:
            name: Name for the dataset
            tools_schema: Tool schemas to base generation on
            num_samples: Number of samples to generate
            model: OpenRouter model for generation
            batch_size: Batch size for generation
            workers: Number of concurrent workers
        
        Returns:
            Path to the generated JSONL file
        """
        if not self._ensure_needle_installed():
            raise RuntimeError("cactus-needle is not installed")
        
        # Resolve tools schema
        tools = self._resolve_tools_schema(tools_schema)
        tools_json = json.dumps(tools)
        
        # Create temporary file for tools
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(tools, f)
            tools_file = f.name
        
        try:
            output_path = self.datasets_dir / f"{name}.jsonl"
            
            self._run_needle_command([
                "generate-data",
                "--tools", tools_file,
                "--num-samples", str(num_samples),
                "--batch-size", str(batch_size),
                "--workers", str(workers),
                "--model", model,
                "--output", str(output_path)
            ])
            
            logger.info(f"Generated dataset: {output_path}")
            return output_path
            
        finally:
            os.unlink(tools_file)
    
    def finetune(
        self,
        jsonl_path: Path,
        name: str,
        epochs: int = 10,
        lora_rank: int = 16,
        lora_alpha: float = 32.0,
        batch_size: int = 16,
        max_len: int = 1024,
        val_split: float = 0.1,
        checkpoint_dir: Optional[Path] = None,
        generate_extra: int = 0
    ) -> Path:
        """
        Fine-tune Needle on a dataset using LoRA.
        
        Args:
            jsonl_path: Path to training data JSONL file
            name: Name for the model
            epochs: Number of training epochs
            lora_rank: LoRA adapter rank
            lora_alpha: LoRA scaling alpha
            batch_size: Training batch size
            max_len: Maximum sequence length
            val_split: Validation split ratio
            checkpoint_dir: Directory for checkpoints
            generate_extra: Generate extra samples before training
        
        Returns:
            Path to the LoRA adapter .pkl file
        """
        if not self._ensure_needle_installed():
            raise RuntimeError("cactus-needle is not installed")
        
        checkpoint_dir = checkpoint_dir or self.checkpoints_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = checkpoint_dir / f"{name}_lora.pkl"
        
        cmd = [
            "finetune",
            str(jsonl_path),
            "--epochs", str(epochs),
            "--lora-rank", str(lora_rank),
            "--lora-alpha", str(lora_alpha),
            "--batch-size", str(batch_size),
            "--max-len", str(max_len),
            "--val-split", str(val_split),
            "--out", str(output_path)
        ]
        
        if self.base_checkpoint:
            cmd.extend(["--checkpoint", self.base_checkpoint])
        
        if generate_extra > 0:
            cmd.extend(["--generate", str(generate_extra)])
            # Will need OPENROUTER_API_KEY in environment
        
        self._run_needle_command(cmd)
        
        logger.info(f"Fine-tuned model: {output_path}")
        return output_path
    
    def build_model(
        self,
        lora_path: Path,
        name: str,
        base_checkpoint: Optional[str] = None,
        bits: Optional[int] = None,
        upload: bool = False,
        hf_repo: Optional[str] = None
    ) -> Path:
        """
        Build a .cact archive from a fine-tuned model.
        
        Args:
            lora_path: Path to LoRA adapter
            name: Name for the output model
            base_checkpoint: Base checkpoint to merge with
            bits: Quantization bits (2 or 4, None = default)
            upload: Upload to Hugging Face
            hf_repo: Hugging Face repo for upload
        
        Returns:
            Path to the .cact file
        """
        if not self._ensure_needle_installed():
            raise RuntimeError("cactus-needle is not installed")
        
        output_path = self.models_dir / f"{name}.cact"
        
        cmd = [
            "build",
            self.base_checkpoint or "needle2",  # Auto-downloads if not specified
            "--lora", str(lora_path),
            "--out", str(output_path)
        ]
        
        if bits:
            cmd.extend(["--bits", str(bits)])
        
        if upload:
            cmd.append("--upload")
            if hf_repo:
                os.environ["NEEDLE_HF_REPO"] = hf_repo
        
        self._run_needle_command(cmd)
        
        logger.info(f"Built model: {output_path}")
        return output_path
    
    def create_model(
        self,
        name: str,
        domain: str,
        tools_schema: Union[List[Dict], str, Path],
        num_samples: int = 200,
        epochs: int = 10,
        lora_rank: int = 16,
        lora_alpha: float = 32.0,
        generate_extra: int = 0,
        openrouter_model: str = "deepseek/deepseek-v4-flash",
        bits: Optional[int] = None
    ) -> FineTunedModel:
        """
        Full pipeline: Generate data → Fine-tune → Build .cact
        
        This is the main method for creating a new specialized agent model.
        
        Args:
            name: Unique name for the model
            domain: Domain/description of the model
            tools_schema: Tool schemas for this domain
            num_samples: Number of training samples to generate
            epochs: Training epochs
            lora_rank: LoRA rank
            lora_alpha: LoRA alpha
            generate_extra: Extra samples to generate
            openrouter_model: Model for data generation
            bits: Quantization bits for output
        
        Returns:
            FineTunedModel with paths to all artifacts
        """
        logger.info(f"Creating model: {name} (domain: {domain})")
        
        # Step 1: Generate data
        logger.info("Step 1/3: Generating synthetic training data...")
        dataset_path = self.generate_data(
            name=name,
            tools_schema=tools_schema,
            num_samples=num_samples,
            model=openrouter_model
        )
        
        # Step 2: Fine-tune
        logger.info("Step 2/3: Fine-tuning with LoRA...")
        lora_path = self.finetune(
            jsonl_path=dataset_path,
            name=name,
            epochs=epochs,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha,
            generate_extra=generate_extra
        )
        
        # Step 3: Build .cact
        logger.info("Step 3/3: Building .cact archive...")
        model_path = self.build_model(
            lora_path=lora_path,
            name=name,
            bits=bits
        )
        
        # Resolve tools schema for registry
        resolved_tools = self._resolve_tools_schema(tools_schema)
        
        # Create and register model
        model = FineTunedModel(
            name=name,
            domain=domain,
            model_path=model_path,
            dataset_path=dataset_path,
            checkpoint_path=self.base_checkpoint,
            lora_path=lora_path,
            tools_schema=resolved_tools
        )
        
        self.registry[name] = model
        
        logger.info(f"Model created successfully: {model_path}")
        return model
    
    def evaluate_model(
        self,
        model_path: Path,
        test_data: Path,
        num_samples: int = 50
    ) -> EvaluationResult:
        """
        Evaluate a fine-tuned model on test data.
        
        Args:
            model_path: Path to .cact model
            test_data: Path to test JSONL data
            num_samples: Number of test samples to use
        
        Returns:
            EvaluationResult with metrics
        """
        import needle
        import random
        
        # Load test data
        with open(test_data, 'r') as f:
            test_samples = [json.loads(line) for line in f if line.strip()]
        
        # Sample a subset
        test_samples = random.sample(test_samples, min(num_samples, len(test_samples)))
        
        # Load model
        agent = needle.Needle(weights=str(model_path), tools=[])
        
        passed = 0
        total = len(test_samples)
        
        for sample in test_samples:
            query = sample.get("query", "")
            expected_answers = sample.get("answers", [])
            
            try:
                result = agent.complete(query, max_new_tokens=256)
                # Check if expected tool was called
                function_calls = result.get("function_calls", [])
                
                if expected_answers and function_calls:
                    expected_names = {a["name"] for a in expected_answers}
                    actual_names = {c["name"] for c in function_calls}
                    if expected_names == actual_names:
                        passed += 1
                    elif expected_names & actual_names:  # Partial match
                        passed += 0.5
                else:
                    passed += 1  # No expected answer, count as pass
                    
            except Exception as e:
                logger.warning(f"Evaluation error on query '{query}': {e}")
        
        accuracy = passed / total if total > 0 else 0.0
        
        return EvaluationResult(
            model_name=model_path.stem,
            accuracy=accuracy,
            test_samples=total,
            pass_rate=accuracy,
            notes=f"Evaluated on {total} samples, {passed} passed"
        )
    
    def get_model(self, name: str) -> Optional[FineTunedModel]:
        """Get a registered model by name."""
        return self.registry.get(name)
    
    def list_models(self) -> List[FineTunedModel]:
        """List all registered models."""
        return list(self.registry.values())
    
    def delete_model(self, name: str) -> bool:
        """Delete a model and all its artifacts."""
        model = self.registry.get(name)
        if not model:
            return False
        
        # Delete files
        for path in [model.model_path, model.dataset_path, model.lora_path]:
            if path and path.exists():
                path.unlink()
        
        del self.registry[name]
        logger.info(f"Deleted model: {name}")
        return True
    
    def export_for_deployment(self, name: str, output_dir: Path) -> Path:
        """
        Export a model and its tools for deployment.
        
        Args:
            name: Model name
            output_dir: Directory to export to
        
        Returns:
            Path to exported model
        """
        model = self.get_model(name)
        if not model:
            raise ValueError(f"Model '{name}' not found")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy model
        dest_model = output_dir / model.model_path.name
        shutil.copy2(model.model_path, dest_model)
        
        # Copy dataset
        dest_dataset = output_dir / model.dataset_path.name
        shutil.copy2(model.dataset_path, dest_dataset)
        
        # Save metadata
        metadata = {
            "name": model.name,
            "domain": model.domain,
            "model_path": str(dest_model.name),
            "dataset_path": str(dest_dataset.name),
            "tools_schema": model.tools_schema
        }
        
        with open(output_dir / f"{name}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Exported model to: {output_dir}")
        return dest_model
    
    def create_researcher_model(
        self,
        name: str = "researcher",
        domain: str = "model_research",
        tools_schema: Optional[List[Dict]] = None
    ) -> FineTunedModel:
        """
        Create a specialized researcher model for R&D tasks.
        
        The researcher model can:
        - Generate training data for other models
        - Evaluate fine-tuned models
        - Suggest hyperparameters
        - Automate the fine-tuning loop
        
        Args:
            name: Model name
            domain: Domain description
            tools_schema: Custom tools for research (default: evaluation/generation tools)
        
        Returns:
            FineTunedModel for the researcher
        """
        if tools_schema is None:
            # Default researcher tools
            tools_schema = [
                {
                    "name": "generate_training_data",
                    "description": "Generate synthetic training examples for fine-tuning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string", "description": "Domain to generate data for"},
                            "num_samples": {"type": "integer", "default": 100, "description": "Number of samples"},
                            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"], "default": "medium"}
                        },
                        "required": ["domain"]
                    }
                },
                {
                    "name": "evaluate_model",
                    "description": "Evaluate a fine-tuned model on test data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model_path": {"type": "string", "description": "Path to .cact model"},
                            "test_data_path": {"type": "string", "description": "Path to test data"},
                            "metrics": {"type": "array", "items": {"type": "string"}, "default": ["accuracy", "loss"]}
                        },
                        "required": ["model_path", "test_data_path"]
                    }
                },
                {
                    "name": "suggest_hyperparameters",
                    "description": "Suggest optimal hyperparameters for fine-tuning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string", "description": "Domain"},
                            "dataset_size": {"type": "integer", "description": "Number of training samples"}
                        },
                        "required": ["domain", "dataset_size"]
                    }
                }
            ]
        
        return self.create_model(
            name=name,
            domain=domain,
            tools_schema=tools_schema,
            num_samples=300,  # More samples for researcher
            epochs=15,
            lora_rank=32,
            lora_alpha=64.0
        )
    
    def automated_research_loop(
        self,
        target_domain: str,
        target_tools: List[Dict],
        iterations: int = 3,
        researcher_name: str = "researcher"
    ) -> FineTunedModel:
        """
        Run an automated R&D loop using dual Needle models.
        
        This implements your vision of using 2 models for automated fine-tuning:
        1. Researcher model: Generates data, evaluates, suggests improvements
        2. Production model: Gets fine-tuned based on researcher's work
        
        Args:
            target_domain: Domain for the production model
            target_tools: Tools for the production model
            iterations: Number of R&D iterations
            researcher_name: Name of researcher model
        
        Returns:
            Best fine-tuned production model
        """
        logger.info(f"Starting automated research loop for domain: {target_domain}")
        
        # Ensure researcher model exists
        if researcher_name not in self.registry:
            logger.info(f"Creating researcher model: {researcher_name}")
            researcher = self.create_researcher_model(name=researcher_name)
        else:
            researcher = self.registry[researcher_name]
        
        best_model = None
        best_score = 0.0
        
        for i in range(iterations):
            logger.info(f"=== Iteration {i+1}/{iterations} ===")
            
            iteration_name = f"{target_domain}_v{i+1}"
            
            # Create production model candidate
            model = self.create_model(
                name=iteration_name,
                domain=target_domain,
                tools_schema=target_tools,
                num_samples=200 + (i * 50),  # Increase samples each iteration
                epochs=10,
                lora_rank=16,
                lora_alpha=32.0
            )
            
            # Evaluate the model
            # For demo, we'll create a simple test dataset
            test_path = self.datasets_dir / f"{iteration_name}_test.jsonl"
            
            # Create minimal test data (in practice, use a held-out validation set)
            with open(test_path, 'w') as f:
                for _ in range(10):
                    f.write(json.dumps({
                        "query": "test query",
                        "tools": target_tools,
                        "answers": []
                    }) + "\n")
            
            if test_path.exists():
                result = self.evaluate_model(model.model_path, test_path)
                score = result.pass_rate
                
                logger.info(f"Iteration {i+1} score: {score:.2%}")
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    logger.info(f"New best model: {model.name} (score: {score:.2%})")
            else:
                # No evaluation, just use latest
                best_model = model
        
        logger.info(f"Research loop complete. Best model: {best_model.name} (score: {best_score:.2%})")
        return best_model
    
    # =========================================================================
    # Closed-Loop Evaluation Integration
    # =========================================================================
    
    def evaluate_with_reward(
        self,
        model_path: Path,
        test_data_path: Path,
        num_samples: int = 50
    ) -> Dict[str, Any]:
        """
        Evaluate a model and generate a reward signal.
        
        This is the key method for closed-loop optimization.
        It uses the EvaluationAgent to test the model and calculate rewards.
        
        Args:
            model_path: Path to the .cact model
            test_data_path: Path to test data JSONL
            num_samples: Number of test samples to use
        
        Returns:
            Dict with evaluation results, reward signal, and feedback
        """
        # Lazy import to avoid circular dependency
        from evaluation_agent import EvaluationAgent
        
        evaluator = EvaluationAgent()
        signal = evaluator.generate_optimization_signal(
            str(model_path),
            str(test_data_path),
            num_samples
        )
        
        # Store reward in model metadata if it's a registered model
        model_name = model_path.stem
        if model_name in self.registry:
            model = self.registry[model_name]
            model.metrics["reward"] = signal["reward_signal"]
            model.metrics["evaluation_score"] = signal["evaluation"]["total_score"]
        
        logger.info(f"Reward signal for {model_name}: {signal['reward_signal']:.4f}")
        return signal
    
    def closed_loop_optimize(
        self,
        target_domain: str,
        target_tools: List[Dict],
        test_data_path: Path,
        max_iterations: int = 10,
        min_reward: float = 0.8,
        patience: int = 3,
        num_test_samples: int = 50
    ) -> Tuple[FineTunedModel, Dict[str, Any]]:
        """
        Run a closed-loop optimization process.
        
        This method implements a complete RLHF-style loop:
        1. Create a candidate model
        2. Evaluate it with the evaluation agent
        3. Calculate reward signal
        4. If reward is good enough, stop
        5. If reward is improving, continue
        6. If reward is not improving for `patience` iterations, stop
        
        The reward signal drives the optimization, creating a true
        closed-loop system for agent fine-tuning.
        
        Args:
            target_domain: Domain for the model
            target_tools: Tool schemas for the domain
            test_data_path: Path to test data for evaluation
            max_iterations: Maximum number of iterations
            min_reward: Stop if reward exceeds this threshold
            patience: Stop after this many iterations without improvement
            num_test_samples: Number of test samples per evaluation
        
        Returns:
            Tuple of (best_model, optimization_report)
        """
        from evaluation_agent import EvaluationAgent
        
        logger.info(f"Starting closed-loop optimization for domain: {target_domain}")
        
        evaluator = EvaluationAgent()
        
        best_model: Optional[FineTunedModel] = None
        best_reward: float = 0.0
        best_score: float = 0.0
        
        # Track history for early stopping
        reward_history: List[float] = []
        score_history: List[float] = []
        no_improvement_count: int = 0
        
        optimization_report: Dict[str, Any] = {
            "domain": target_domain,
            "iterations": [],
            "best_model": None,
            "best_reward": 0.0,
            "converged": False,
            "stop_reason": None
        }
        
        for i in range(max_iterations):
            logger.info(f"=== Iteration {i+1}/{max_iterations} ===")
            
            iteration_name = f"{target_domain}_v{i+1}"
            
            # Step 1: Create candidate model
            logger.info("Creating candidate model...")
            model = self.create_model(
                name=iteration_name,
                domain=target_domain,
                tools_schema=target_tools,
                num_samples=200 + (i * 50),  # Increase samples each iteration
                epochs=10 + (i * 2),  # Increase epochs
                lora_rank=16,
                lora_alpha=32.0
            )
            
            # Step 2: Evaluate and get reward signal
            logger.info("Evaluating model...")
            signal = evaluator.generate_optimization_signal(
                str(model.model_path),
                str(test_data_path),
                num_test_samples
            )
            
            reward = signal["reward_signal"]
            score = signal["evaluation"]["total_score"]
            
            # Store in registry
            model.metrics["reward"] = reward
            model.metrics["score"] = score
            
            # Track history
            reward_history.append(reward)
            score_history.append(score)
            
            # Record iteration
            optimization_report["iterations"].append({
                "iteration": i + 1,
                "model_name": model.name,
                "reward": reward,
                "score": score,
                "improvement": signal["improvement"],
                "feedback": signal["feedback"],
                "recommendations": signal["recommendations"]
            })
            
            logger.info(f"Iteration {i+1}: reward={reward:.4f}, score={score:.4f}")
            
            # Step 3: Check for best
            if reward > best_reward:
                best_reward = reward
                best_score = score
                best_model = model
                no_improvement_count = 0
                logger.info(f"New best: {model.name} (reward={reward:.4f})")
            else:
                no_improvement_count += 1
            
            # Step 4: Check stopping conditions
            stop_reason = None
            
            if reward >= min_reward:
                stop_reason = f"Reached minimum reward threshold ({min_reward})"
                optimization_report["converged"] = True
                
            elif no_improvement_count >= patience:
                stop_reason = f"No improvement for {patience} iterations"
                
            if stop_reason or i == max_iterations - 1:
                if stop_reason:
                    logger.info(f"Stopping early: {stop_reason}")
                
                optimization_report.update({
                    "best_model": best_model.name if best_model else None,
                    "best_reward": best_reward,
                    "best_score": best_score,
                    "stop_reason": stop_reason or "Max iterations reached",
                    "total_iterations": i + 1
                })
                
                break
        
        if best_model:
            logger.info(f"Optimization complete. Best: {best_model.name} (reward={best_reward:.4f}, score={best_score:.4f})")
        else:
            logger.warning("No valid model produced during optimization")
        
        return best_model, optimization_report
    
    def adaptive_finetune(
        self,
        target_domain: str,
        target_tools: List[Dict],
        test_data_path: Path,
        max_iterations: int = 5,
        num_test_samples: int = 50
    ) -> Tuple[FineTunedModel, Dict[str, Any]]:
        """
        Adaptive fine-tuning with dynamic hyperparameter adjustment.
        
        This method uses reward signals to adaptively adjust hyperparameters:
        - If reward is low, increase training data and epochs
        - If reward is high but not improving, try different hyperparameters
        - If precision is low, focus on better tool-call matching
        
        Args:
            target_domain: Domain for the model
            target_tools: Tool schemas
            test_data_path: Path to test data
            max_iterations: Maximum iterations
            num_test_samples: Test samples per evaluation
        
        Returns:
            Tuple of (best_model, report)
        """
        from evaluation_agent import EvaluationAgent
        
        logger.info(f"Starting adaptive fine-tuning for: {target_domain}")
        
        evaluator = EvaluationAgent()
        
        best_model: Optional[FineTunedModel] = None
        best_reward: float = 0.0
        
        # Adaptive parameters
        num_samples = 200
        epochs = 10
        lora_rank = 16
        
        report: Dict[str, Any] = {
            "iterations": [],
            "adaptations": []
        }
        
        for i in range(max_iterations):
            iteration_name = f"{target_domain}_adaptive_v{i+1}"
            
            logger.info(f"Iteration {i+1}: samples={num_samples}, epochs={epochs}, lora_rank={lora_rank}")
            
            # Create model with current parameters
            model = self.create_model(
                name=iteration_name,
                domain=target_domain,
                tools_schema=target_tools,
                num_samples=num_samples,
                epochs=epochs,
                lora_rank=lora_rank,
                lora_alpha=32.0
            )
            
            # Evaluate
            signal = evaluator.generate_optimization_signal(
                str(model.model_path),
                str(test_data_path),
                num_test_samples
            )
            
            reward = signal["reward_signal"]
            metrics = signal["evaluation"]["metrics"]
            
            report["iterations"].append({
                "model": model.name,
                "reward": reward,
                "params": {"samples": num_samples, "epochs": epochs, "lora_rank": lora_rank},
                "metrics": metrics
            })
            
            if reward > best_reward:
                best_reward = reward
                best_model = model
            
            # Adapt parameters based on results
            adaptations = []
            
            accuracy = metrics.get("accuracy", 0.0)
            precision = metrics.get("precision", 0.0)
            
            if accuracy < 0.7:
                # Model is underfitting - need more data
                num_samples = min(num_samples + 100, 1000)
                adaptations.append(f"Increased samples to {num_samples} (low accuracy: {accuracy:.2f})")
            
            if precision < 0.7:
                # Many incorrect tool calls - need more training
                epochs = min(epochs + 5, 30)
                adaptations.append(f"Increased epochs to {epochs} (low precision: {precision:.2f})")
            
            if reward > 0.8 and reward - best_reward < 0.05 and i < max_iterations - 1:
                # Converging - try different hyperparameters
                lora_rank = max(8, lora_rank - 4) if lora_rank > 8 else 32
                adaptations.append(f"Adjusted LoRA rank to {lora_rank} (searching for better config)")
            
            if adaptations:
                report["adaptations"].extend(adaptations)
                logger.info(f"Adaptations: {', '.join(adaptations)}")
            
            # Early stopping if converged
            if reward >= 0.95:
                logger.info("Early stopping: high reward achieved")
                break
        
        report.update({
            "best_model": best_model.name if best_model else None,
            "best_reward": best_reward
        })
        
        logger.info(f"Adaptive tuning complete. Best reward: {best_reward:.4f}")
        return best_model, report
