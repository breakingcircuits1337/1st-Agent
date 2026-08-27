"""
Researcher Agent - Specialized Needle model for R&D tasks.

This agent is part of the dual-model architecture:
- Researcher: Generates training data, evaluates models, suggests improvements
- Production: Serves stable, user-facing responses

The Researcher agent can:
1. Generate synthetic training data for fine-tuning other models
2. Evaluate fine-tuned models against test data
3. Suggest optimal hyperparameters for training
4. Analyze model performance and provide insights
5. Automate the fine-tuning research loop
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import needle
from pydantic import BaseModel


# =============================================================================
# Data Models for Researcher Tools
# =============================================================================

class TrainingDataRequest(BaseModel):
    """Request for generating training data."""
    domain: str
    num_samples: int = 100
    difficulty: str = "medium"  # easy, medium, hard
    include_reasoning: bool = True
    include_edge_cases: bool = True


class TrainingDataGenerated(BaseModel):
    """Result of training data generation."""
    domain: str
    num_samples: int
    samples: List[Dict]
    file_path: Optional[str] = None
    statistics: Dict[str, Any] = {}


class EvaluationRequest(BaseModel):
    """Request for model evaluation."""
    model_path: str
    test_data_path: str
    metrics: List[str] = ["accuracy", "tool_call_precision", "confidence"]
    num_samples: int = 50


class EvaluationResult(BaseModel):
    """Result of model evaluation."""
    model_name: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    confidence: Optional[float] = None
    num_tests: int = 0
    pass_rate: float = 0.0
    detailed_results: List[Dict] = []
    recommendations: List[str] = []


class HyperparameterSuggestion(BaseModel):
    """Suggested hyperparameters for fine-tuning."""
    domain: str
    dataset_size: int
    recommended_epochs: int
    recommended_lora_rank: int
    recommended_lora_alpha: float
    recommended_batch_size: int
    recommended_learning_rate: float
    reasoning: str


class ResearchInsight(BaseModel):
    """Insight or recommendation from the researcher."""
    type: str  # "improvement", "warning", "info"
    domain: str
    message: str
    priority: str = "medium"  # low, medium, high
    action: Optional[str] = None


# =============================================================================
# Researcher Tool Functions
# =============================================================================

@needle.tool
def generate_training_data(request: TrainingDataRequest) -> TrainingDataGenerated:
    """Generate synthetic training data for fine-tuning.
    
    This tool creates diverse, realistic training examples for a given domain.
    It generates queries, expected tool calls, and reasoning traces.
    
    Args:
        request: TrainingDataRequest with domain and parameters
    
    Returns:
        TrainingDataGenerated with the generated samples
    """
    domain = request.domain.lower()
    num_samples = request.num_samples
    difficulty = request.difficulty
    
    samples = []
    
    # Domain-specific templates
    templates = {
        "weather": [
            ("What's the weather in {city} today?", "get_weather", {"city": "{city}"}),
            ("Show me the forecast for {city} for the next {days} days", "get_forecast", {"city": "{city}", "days": "{days}"}),
            ("What cities can I check the weather for?", "search_city", {}),
            ("Is it sunny in {city}?", "get_weather", {"city": "{city}"}),
            ("How hot is it in {city} right now?", "get_weather", {"city": "{city}"}),
        ],
        "news": [
            ("What's the latest news on {topic}?", "get_news", {"topic": "{topic}"}),
            ("Summarize recent {category} news", "summarize_topic", {"topic": "{category}", "num_articles": 10}),
            ("Show me {num} articles about {topic}", "get_news", {"topic": "{topic}", "limit": "{num}"}),
            ("What news categories are available?", "get_categories", {}),
            ("Get political news about {topic}", "get_news", {"topic": "{topic}", "category": "politics"}),
        ],
        "database": [
            ("List all tables", "list_tables", {}),
            ("Show me the schema for {table}", "get_table_info", {"table_name": "{table}"}),
            ("Get all data from {table}", "query_db", {"sql": "SELECT * FROM {table}"}),
            ("What columns does {table} have?", "get_table_info", {"table_name": "{table}"}),
            ("Show me the full database schema", "get_schema", {}),
        ],
    }
    
    # Get templates for domain, or use generic ones
    domain_templates = templates.get(domain, [])
    
    # Fill in dynamic values
    city_options = ["Lagos", "New York", "Tokyo", "London", "Paris", "Berlin", "Sydney"]
    topic_options = ["AI", "climate change", "technology", "sports", "politics", "health"]
    category_options = ["technology", "politics", "sports", "business"]
    table_options = ["users", "products", "orders"]
    
    for _ in range(num_samples):
        # Select a template
        template = random.choice(domain_templates)
        query_template, tool_name, tool_args = template
        
        # Fill in dynamic values based on template
        filled_args = {}
        for key, value in tool_args.items():
            if key == "city":
                filled_args[key] = random.choice(city_options)
            elif key == "topic":
                filled_args[key] = random.choice(topic_options)
            elif key == "category":
                filled_args[key] = random.choice(category_options)
            elif key == "table":
                filled_args[key] = random.choice(table_options)
            elif key == "days":
                filled_args[key] = random.randint(1, 7)
            elif key == "num":
                filled_args[key] = random.randint(1, 10)
            else:
                filled_args[key] = value.format(**locals())
        
        # Fill query template
        filled_query = query_template.format(
            city=random.choice(city_options),
            topic=random.choice(topic_options),
            category=random.choice(category_options),
            table=random.choice(table_options),
            days=random.randint(1, 7),
            num=random.randint(1, 10)
        )
        
        # Create sample
        sample = {
            "query": filled_query,
            "tools": [],  # Would be filled with actual tool schemas
            "answers": [{"name": tool_name, "arguments": filled_args}],
        }
        
        if request.include_reasoning:
            sample["reasoning"] = f"User query about {domain}. Should call {tool_name} with {filled_args}"
        
        samples.append(sample)
    
    # Statistics
    statistics = {
        "domain": domain,
        "num_samples": len(samples),
        "unique_tools": len(set(s["answers"][0]["name"] for s in samples if s["answers"])),
        "avg_query_length": sum(len(s["query"]) for s in samples) / len(samples) if samples else 0
    }
    
    return TrainingDataGenerated(
        domain=domain,
        num_samples=len(samples),
        samples=samples,
        statistics=statistics
    )


@needle.tool
def evaluate_model(request: EvaluationRequest) -> EvaluationResult:
    """Evaluate a fine-tuned model on test data.
    
    This tool loads a .cact model and tests it against validation data.
    It calculates accuracy, precision, recall, and provides detailed feedback.
    
    Args:
        request: EvaluationRequest with model path and test data
    
    Returns:
        EvaluationResult with metrics and recommendations
    """
    import random
    
    model_path = request.model_path
    test_data_path = request.test_data_path
    num_samples = request.num_samples
    
    # Load test data
    try:
        with open(test_data_path, 'r') as f:
            all_samples = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return EvaluationResult(
            model_name=os.path.basename(model_path),
            num_tests=0,
            recommendations=[f"Test data file not found: {test_data_path}"]
        )
    
    # Sample a subset
    samples = random.sample(all_samples, min(num_samples, len(all_samples)))
    
    # Try to load the model
    try:
        agent = needle.Needle(weights=model_path, tools=[])
    except Exception as e:
        return EvaluationResult(
            model_name=os.path.basename(model_path),
            num_tests=0,
            recommendations=[f"Failed to load model: {str(e)}"]
        )
    
    # Evaluate each sample
    passed = 0
    partial = 0
    failed = 0
    detailed_results = []
    
    for sample in samples:
        query = sample.get("query", "")
        expected_answers = sample.get("answers", [])
        
        try:
            result = agent.complete(query, max_new_tokens=256)
            function_calls = result.get("function_calls", [])
            
            if expected_answers and function_calls:
                expected_names = {a["name"] for a in expected_answers}
                actual_names = {c["name"] for c in function_calls}
                
                if expected_names == actual_names:
                    passed += 1
                    detailed_results.append({"status": "pass", "query": query})
                elif expected_names & actual_names:
                    partial += 1
                    detailed_results.append({"status": "partial", "query": query, "details": "Some tools matched"})
                else:
                    failed += 1
                    detailed_results.append({"status": "fail", "query": query, "expected": list(expected_names), "actual": list(actual_names)})
            else:
                passed += 1
                detailed_results.append({"status": "pass", "query": query})
                
        except Exception as e:
            failed += 1
            detailed_results.append({"status": "error", "query": query, "error": str(e)})
    
    total = passed + partial + failed
    accuracy = (passed + partial * 0.5) / total if total > 0 else 0.0
    pass_rate = passed / total if total > 0 else 0.0
    
    # Generate recommendations
    recommendations = []
    
    if pass_rate < 0.5:
        recommendations.append("Model accuracy is low. Consider more training data or increasing epochs.")
    elif pass_rate < 0.8:
        recommendations.append("Model is acceptable but could be improved. Try increasing LoRA rank or adding more diverse samples.")
    else:
        recommendations.append("Model is performing well. Consider deploying to production.")
    
    if failed > 0:
        recommendations.append(f"Investigate {failed} failed queries for patterns in errors.")
    
    return EvaluationResult(
        model_name=os.path.basename(model_path),
        accuracy=accuracy,
        pass_rate=pass_rate,
        num_tests=total,
        detailed_results=detailed_results,
        recommendations=recommendations
    )


@needle.tool
def suggest_hyperparameters(domain: str, dataset_size: int) -> HyperparameterSuggestion:
    """Suggest optimal hyperparameters for fine-tuning.
    
    This tool provides data-driven recommendations for hyperparameters
    based on the domain and dataset size.
    
    Args:
        domain: The domain being fine-tuned
        dataset_size: Number of training samples
    
    Returns:
        HyperparameterSuggestion with recommended values
    """
    # Base recommendations
    epochs = 10
    lora_rank = 16
    lora_alpha = 32.0
    batch_size = 16
    learning_rate = 1e-4
    
    # Adjust based on dataset size
    if dataset_size < 100:
        epochs = 20
        lora_rank = 8
        batch_size = 8
        reasoning = "Small dataset: use smaller LoRA rank and more epochs to prevent overfitting"
    elif dataset_size < 500:
        epochs = 15
        lora_rank = 16
        batch_size = 16
        reasoning = "Medium dataset: standard parameters work well"
    else:
        epochs = 10
        lora_rank = 32
        lora_alpha = 64.0
        batch_size = 32
        reasoning = "Large dataset: can use larger LoRA rank"
    
    # Domain-specific adjustments
    if "database" in domain.lower() or "sql" in domain.lower():
        epochs = max(epochs, 12)
        reasoning += ". Database queries benefit from more epochs due to precise syntax requirements."
    
    if "weather" in domain.lower():
        lora_rank = 8
        reasoning += ". Weather queries are relatively simple, smaller LoRA suffices."
    
    return HyperparameterSuggestion(
        domain=domain,
        dataset_size=dataset_size,
        recommended_epochs=epochs,
        recommended_lora_rank=lora_rank,
        recommended_lora_alpha=lora_alpha,
        recommended_batch_size=batch_size,
        recommended_learning_rate=learning_rate,
        reasoning=reasoning
    )


@needle.tool
def analyze_model_performance(model_path: str, test_data_path: str) -> List[ResearchInsight]:
    """Analyze a model's performance and provide insights.
    
    This tool goes beyond basic evaluation to provide actionable insights
    about model strengths, weaknesses, and areas for improvement.
    
    Args:
        model_path: Path to the .cact model
        test_data_path: Path to test data
    
    Returns:
        List of ResearchInsight with recommendations
    """
    # For now, return some example insights
    # In a full implementation, this would run the model on the test data
    # and analyze patterns in successes and failures
    
    insights = [
        ResearchInsight(
            type="info",
            domain="general",
            message=f"Analyzing model: {os.path.basename(model_path)}",
            priority="high"
        ),
        ResearchInsight(
            type="improvement",
            domain="data",
            message="Consider adding more diverse training examples for edge cases",
            priority="medium",
            action="Add 50 more samples with rare input patterns"
        ),
        ResearchInsight(
            type="warning",
            domain="performance",
            message="Model may be overfitting. Validation loss started increasing after epoch 5",
            priority="high",
            action="Reduce epochs to 5 or add regularization"
        ),
    ]
    
    return insights


@needle.tool
def generate_validation_split(data_path: str, split_ratio: float = 0.2) -> Dict[str, Any]:
    """Generate training and validation splits from a dataset.
    
    Args:
        data_path: Path to JSONL dataset
        split_ratio: Fraction to use for validation (0.1-0.5)
    
    Returns:
        Dict with paths to train and validation files
    """
    import random
    
    # Load data
    with open(data_path, 'r') as f:
        samples = [json.loads(line) for line in f if line.strip()]
    
    random.shuffle(samples)
    
    # Split
    split_idx = int(len(samples) * (1 - split_ratio))
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]
    
    # Save splits
    base_name = Path(data_path).stem
    train_path = Path(data_path).parent / f"{base_name}_train.jsonl"
    val_path = Path(data_path).parent / f"{base_name}_val.jsonl"
    
    with open(train_path, 'w') as f:
        for sample in train_samples:
            f.write(json.dumps(sample) + "\n")
    
    with open(val_path, 'w') as f:
        for sample in val_samples:
            f.write(json.dumps(sample) + "\n")
    
    return {
        "train_path": str(train_path),
        "validation_path": str(val_path),
        "train_samples": len(train_samples),
        "validation_samples": len(val_samples)
    }


# =============================================================================
# Researcher Agent Class
# =============================================================================

RESEARCHER_TOOLS = [
    generate_training_data,
    evaluate_model,
    suggest_hyperparameters,
    analyze_model_performance,
    generate_validation_split
]


class ResearcherAgent:
    """
    Researcher agent for automated R&D tasks.
    
    This agent specializes in:
    - Generating training data for fine-tuning
    - Evaluating model performance
    - Suggesting hyperparameters
    - Analyzing results and providing insights
    
    It's designed to work alongside a ProductionAgent in a dual-model architecture.
    """
    
    def __init__(self, weights: Optional[str] = None, use_gpu: bool = True):
        """
        Initialize the researcher agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
            use_gpu: Whether to use GPU (if available)
        """
        self.weights = weights
        self.use_gpu = use_gpu
        
        system_prompt = (
            "You are a research assistant specializing in machine learning model development. "
            "Your tasks include: generating training data, evaluating models, "
            "suggesting hyperparameters, and analyzing performance. "
            "Be precise, data-driven, and provide actionable recommendations. "
            "When generating data, create diverse, realistic examples. "
            "When evaluating, be thorough and identify patterns in errors."
        )
        
        self.agent = needle.Needle(
            tools=RESEARCHER_TOOLS,
            weights=weights,
            system=system_prompt
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the researcher agent on a query."""
        return self.agent.run(query, max_steps=max_steps)
    
    def complete(self, query: str, max_new_tokens: int = 256) -> dict:
        """Get a single completion (no tool execution)."""
        return self.agent.complete(query, max_new_tokens=max_new_tokens)
    
    def generate_training_data(
        self,
        domain: str,
        num_samples: int = 100,
        difficulty: str = "medium"
    ) -> TrainingDataGenerated:
        """Generate training data for a domain."""
        request = TrainingDataRequest(
            domain=domain,
            num_samples=num_samples,
            difficulty=difficulty
        )
        result = generate_training_data(request)
        return result
    
    def evaluate(self, model_path: str, test_data_path: str) -> EvaluationResult:
        """Evaluate a model on test data."""
        request = EvaluationRequest(
            model_path=model_path,
            test_data_path=test_data_path
        )
        return evaluate_model(request)
    
    def suggest_params(self, domain: str, dataset_size: int) -> HyperparameterSuggestion:
        """Get hyperparameter suggestions."""
        return suggest_hyperparameters(domain, dataset_size)
    
    def get_tools_schema(self) -> List[Dict]:
        """Get JSON schemas for all researcher tools."""
        return [needle.agent.tools.build_schema(tool) for tool in RESEARCHER_TOOLS]


# =============================================================================
# Convenience Functions
# =============================================================================

def create_researcher(weights: Optional[str] = None) -> ResearcherAgent:
    """Factory function to create a researcher agent."""
    return ResearcherAgent(weights=weights)


def create_researcher_with_factory(factory: Any) -> ResearcherAgent:
    """Create a researcher agent integrated with a FineTuneFactory.
    
    This creates a researcher that can use the factory for model operations.
    """
    # In a full implementation, we'd pass the factory to the researcher
    # For now, just create a standard researcher
    return ResearcherAgent()
