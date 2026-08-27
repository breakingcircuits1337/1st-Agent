"""
Production Agent - Stable Needle model for user-facing tasks.

This agent is part of the dual-model architecture:
- Researcher: Generates training data, evaluates models, suggests improvements
- Production: Serves stable, user-facing responses

The Production agent:
1. Handles user queries with specialized domain tools
2. Provides natural language responses
3. Routes complex queries to appropriate specialized agents
4. Maintains stability and reliability for end-users
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass

import needle
from pydantic import BaseModel


# =============================================================================
# Data Models for Production Tools
# =============================================================================

class QueryClassification(BaseModel):
    """Classification of a user query."""
    query: str
    domain: str
    intent: str
    confidence: float
    tools: List[str]


class AgentResponse(BaseModel):
    """Structured response from a production agent."""
    query: str
    domain: str
    answer: str
    tool_calls: List[Dict] = []
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}


class MultiAgentResult(BaseModel):
    """Result from multiple agents."""
    query: str
    agent_results: Dict[str, AgentResponse]
    final_answer: str
    consensus_score: float


# =============================================================================
# Production Tool Functions
# =============================================================================

@needle.tool
def classify_query(query: str) -> QueryClassification:
    """Classify a user query by domain and intent.
    
    This tool analyzes the query to determine which specialized agent
    should handle it, and what tools are likely needed.
    
    Args:
        query: The user's query
    
    Returns:
        QueryClassification with domain, intent, and confidence
    """
    query_lower = query.lower()
    
    # Domain keywords
    domain_keywords = {
        "weather": ["weather", "temperature", "forecast", "rain", "sunny", "cloudy", "humidity", "wind"],
        "news": ["news", "article", "headline", "story", "report", "update", "latest"],
        "database": ["database", "sql", "query", "table", "select", "schema", "data", "records"],
        "general": ["tell me", "what is", "explain", "describe", "information", "knowledge"]
    }
    
    # Intent keywords
    intent_keywords = {
        "get": ["get", "show", "tell", "what's", "what is", "list", "find"],
        "create": ["create", "make", "build", "add", "new"],
        "update": ["update", "change", "modify", "edit", "set"],
        "delete": ["delete", "remove", "erase", "clear"],
        "search": ["search", "find", "look for", "query"]
    }
    
    # Find best matching domain
    best_domain = "general"
    best_confidence = 0.0
    
    for domain, keywords in domain_keywords.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        confidence = matches / len(keywords) if keywords else 0
        
        if confidence > best_confidence:
            best_confidence = confidence
            best_domain = domain
    
    # Find best matching intent
    best_intent = "get"
    for intent, keywords in intent_keywords.items():
        matches = sum(1 for kw in keywords if kw in query_lower)
        if matches > 0:
            best_intent = intent
            break
    
    # Determine likely tools based on domain
    tool_map = {
        "weather": ["get_weather", "get_forecast", "search_city"],
        "news": ["get_news", "summarize_topic", "get_categories"],
        "database": ["query_db", "get_table_info", "get_schema", "list_tables"],
        "general": []
    }
    
    return QueryClassification(
        query=query,
        domain=best_domain,
        intent=best_intent,
        confidence=best_confidence,
        tools=tool_map.get(best_domain, [])
    )


@needle.tool
def route_to_agent(query: str, domain: str) -> Dict[str, Any]:
    """Route a query to the appropriate specialized agent.
    
    This tool determines which agent should handle the query and
    provides the routing information.
    
    Args:
        query: The user's query
        domain: The domain (optional, will auto-detect if not provided)
    
    Returns:
        Dict with agent name, domain, and query
    """
    if not domain:
        # Auto-detect domain
        classification = classify_query(query)
        domain = classification.domain
    
    # Map domains to agent names
    agent_map = {
        "weather": "weather_agent",
        "news": "news_agent",
        "database": "db_agent",
        "general": "general_agent"
    }
    
    agent_name = agent_map.get(domain, "general_agent")
    
    return {
        "query": query,
        "domain": domain,
        "agent": agent_name,
        "needs_tools": True
    }


@needle.tool
def format_response(query: str, tool_results: List[Dict], domain: str) -> str:
    """Format tool results into a natural language response.
    
    This tool takes raw tool outputs and converts them into
    human-readable responses.
    
    Args:
        query: The original user query
        tool_results: List of tool call results
        domain: The domain for context
    
    Returns:
        Natural language response string
    """
    if not tool_results:
        return f"I couldn't retrieve information for: {query}"
    
    # Domain-specific formatting
    if domain == "weather":
        return _format_weather_response(tool_results)
    elif domain == "news":
        return _format_news_response(tool_results)
    elif domain == "database":
        return _format_db_response(tool_results)
    else:
        return _format_generic_response(tool_results)


def _format_weather_response(results: List[Dict]) -> str:
    """Format weather tool results."""
    responses = []
    
    for result in results:
        if "error" in result:
            responses.append(f"Error: {result['error']}")
        elif "city" in result:
            city = result.get("city", "Unknown")
            temp = result.get("temp_c", result.get("temperature_c", "?"))
            condition = result.get("condition", "unknown")
            responses.append(f"Weather in {city}: {temp}C, {condition}")
        elif isinstance(result, list):
            # Forecast
            responses.append("Forecast:")
            for item in result:
                date = item.get("date", "?")
                high = item.get("high_c", "?")
                low = item.get("low_c", "?")
                cond = item.get("condition", "?")
                responses.append(f"  {date}: High {high}C, Low {low}C, {cond}")
        elif isinstance(result, str):
            responses.append(result)
    
    return "\n".join(responses)


def _format_news_response(results: List[Dict]) -> str:
    """Format news tool results."""
    responses = []
    
    for result in results:
        if "error" in result:
            responses.append(f"Error: {result['error']}")
        elif isinstance(result, list):
            for article in result:
                title = article.get("title", "No title")
                summary = article.get("summary", "No summary")
                source = article.get("source", "Unknown")
                responses.append(f"- {title} ({source}): {summary}")
        elif isinstance(result, dict):
            topic = result.get("topic", "News")
            key_points = result.get("key_points", [])
            responses.append(f"{topic} Summary:")
            for point in key_points:
                responses.append(f"  - {point}")
        else:
            responses.append(str(result))
    
    return "\n".join(responses)


def _format_db_response(results: List[Dict]) -> str:
    """Format database tool results."""
    responses = []
    
    for result in results:
        if "error" in result:
            responses.append(f"Error: {result['error']}")
        elif "columns" in result and "rows" in result:
            # Query result
            rows = result.get("rows", [])
            if not rows:
                responses.append("No results found.")
            else:
                responses.append(f"Found {result.get('row_count', len(rows))} rows:")
                for row in rows[:10]:  # Limit to 10 rows
                    responses.append(f"  {row}")
                if len(rows) > 10:
                    responses.append(f"  ... and {len(rows) - 10} more rows")
        elif "tables" in result:
            # Schema result
            tables = result.get("tables", [])
            responses.append(f"Database: {result.get('database_name', 'Unknown')}")
            responses.append("Tables:")
            for table in tables:
                responses.append(f"  - {table.get('name', '?')} ({table.get('row_count', 0)} rows)")
        elif "name" in result and "columns" in result:
            # Table info
            responses.append(f"Table: {result['name']}")
            responses.append("Columns:")
            for col in result["columns"]:
                responses.append(f"  - {col.get('name', '?')}: {col.get('type', '?')}")
        else:
            responses.append(str(result))
    
    return "\n".join(responses)


def _format_generic_response(results: List[Dict]) -> str:
    """Format generic tool results."""
    responses = []
    
    for result in results:
        if "error" in result:
            responses.append(f"Error: {result['error']}")
        elif isinstance(result, dict):
            responses.append(json.dumps(result, indent=2))
        else:
            responses.append(str(result))
    
    return "\n".join(responses)


@needle.tool
def validate_query(query: str) -> Dict[str, Any]:
    """Validate a user query for safety and completeness.
    
    Args:
        query: The user's query
    
    Returns:
        Dict with validation status and suggestions
    """
    query = query.strip()
    
    if not query:
        return {"valid": False, "error": "Empty query", "suggestion": "Please provide a question or request"}
    
    if len(query) > 1000:
        return {"valid": False, "error": "Query too long", "suggestion": "Please shorten your query"}
    
    # Check for potentially harmful content
    # (In a production system, this would be more sophisticated)
    harmful_patterns = ["delete all", "drop database", "shutdown", "reboot"]
    for pattern in harmful_patterns:
        if pattern in query.lower():
            return {"valid": False, "error": "Potentially harmful query", "suggestion": "Please rephrase your request"}
    
    return {"valid": True, "query": query}


# =============================================================================
# Production Agent Class
# =============================================================================

PRODUCTION_TOOLS = [
    classify_query,
    route_to_agent,
    format_response,
    validate_query
]


class ProductionAgent:
    """
    Production agent for user-facing tasks.
    
    This agent specializes in:
    - Understanding and classifying user queries
    - Routing to appropriate specialized agents
    - Formatting responses for end-users
    - Validating inputs for safety
    
    It's designed to work alongside a ResearcherAgent in a dual-model architecture.
    """
    
    def __init__(
        self,
        weights: Optional[str] = None,
        specialized_agents: Optional[Dict[str, Any]] = None,
        use_gpu: bool = True
    ):
        """
        Initialize the production agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
            specialized_agents: Dict of domain -> agent for routing
            use_gpu: Whether to use GPU (if available)
        """
        self.weights = weights
        self.use_gpu = use_gpu
        self.specialized_agents = specialized_agents or {}
        
        system_prompt = (
            "You are a helpful assistant. Your job is to understand user queries, "
            "route them to the appropriate specialized agents, and provide clear, "
            "natural language responses. Always be helpful, accurate, and professional. "
            "If you're unsure about something, say so. Validate queries for safety "
            "and completeness before processing them."
        )
        
        self.agent = needle.Needle(
            tools=PRODUCTION_TOOLS,
            weights=weights,
            system=system_prompt
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the production agent on a query."""
        return self.agent.run(query, max_steps=max_steps)
    
    def complete(self, query: str, max_new_tokens: int = 256) -> dict:
        """Get a single completion (no tool execution)."""
        return self.agent.complete(query, max_new_tokens=max_new_tokens)
    
    def classify(self, query: str) -> QueryClassification:
        """Classify a query by domain and intent."""
        return classify_query(query)
    
    def route_and_execute(self, query: str) -> AgentResponse:
        """
        Full pipeline: classify -> route -> execute -> format.
        
        This is the main method for handling user queries.
        
        Args:
            query: User query
        
        Returns:
            AgentResponse with formatted answer
        """
        # Step 1: Validate
        validation = validate_query(query)
        if not validation.get("valid", False):
            return AgentResponse(
                query=query,
                domain="general",
                answer=validation.get("suggestion", "Invalid query"),
                confidence=0.0
            )
        
        # Step 2: Classify
        classification = self.classify(query)
        domain = classification.domain
        
        # Step 3: Route to specialized agent if available
        if domain in self.specialized_agents:
            agent = self.specialized_agents[domain]
            try:
                result = agent.run(query, max_steps=8)
                return AgentResponse(
                    query=query,
                    domain=domain,
                    answer=self._extract_answer(result),
                    tool_calls=result.get("function_calls", []),
                    confidence=result.get("confidence"),
                    metadata={"agent": domain}
                )
            except Exception as e:
                logger.error(f"Error from {domain} agent: {e}")
                return AgentResponse(
                    query=query,
                    domain=domain,
                    answer=f"Sorry, there was an error processing your request: {str(e)}",
                    confidence=0.0
                )
        
        # Step 4: Use production agent directly
        result = self.run(query, max_steps=8)
        return AgentResponse(
            query=query,
            domain=domain,
            answer=self._extract_answer(result),
            tool_calls=result.get("function_calls", []),
            confidence=result.get("confidence")
        )
    
    def _extract_answer(self, result: dict) -> str:
        """Extract the answer from a result dictionary."""
        # Check for formatted text output
        if "text" in result:
            return result["text"]
        
        # Check for tool results
        if "results" in result:
            # Format tool results
            formatted = format_response(
                query=result.get("query", ""),
                tool_results=result["results"],
                domain=result.get("domain", "general")
            )
            return formatted
        
        return "I couldn't generate a clear answer. Please try rephrasing your question."
    
    def add_specialized_agent(self, domain: str, agent: Any) -> None:
        """Add a specialized agent for a domain."""
        self.specialized_agents[domain] = agent
        logger.info(f"Added specialized agent for domain: {domain}")
    
    def get_tools_schema(self) -> List[Dict]:
        """Get JSON schemas for all production tools."""
        return [needle.agent.tools.build_schema(tool) for tool in PRODUCTION_TOOLS]
    
    def list_domains(self) -> List[str]:
        """List all available domains."""
        return list(self.specialized_agents.keys())


# =============================================================================
# Dual Model System
# =============================================================================

class DualModelSystem:
    """
    Combined system using both Researcher and Production agents.
    
    This implements the dual-model architecture where:
    - Researcher model handles R&D tasks (data generation, evaluation)
    - Production model handles user queries
    - Both models can be fine-tuned .cact files
    """
    
    def __init__(
        self,
        researcher_weights: Optional[str] = None,
        production_weights: Optional[str] = None
    ):
        """
        Initialize the dual model system.
        
        Args:
            researcher_weights: Path to researcher .cact file
            production_weights: Path to production .cact file
        """
        self.researcher = ResearcherAgent(weights=researcher_weights)
        self.production = ProductionAgent(weights=production_weights)
    
    def handle_query(self, query: str) -> AgentResponse:
        """Handle a user query with the production agent."""
        return self.production.route_and_execute(query)
    
    def generate_training_data(self, domain: str, num_samples: int = 100) -> Any:
        """Generate training data for a domain."""
        return self.researcher.generate_training_data(domain, num_samples)
    
    def evaluate_model(self, model_path: str, test_data_path: str) -> Any:
        """Evaluate a model."""
        return self.researcher.evaluate(model_path, test_data_path)
    
    def suggest_params(self, domain: str, dataset_size: int) -> Any:
        """Get hyperparameter suggestions."""
        return self.researcher.suggest_params(domain, dataset_size)
    
    def add_specialized_agent(self, domain: str, agent: Any) -> None:
        """Add a specialized agent to the production system."""
        self.production.add_specialized_agent(domain, agent)


# =============================================================================
# Logger Setup
# =============================================================================

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_production_agent(
    weights: Optional[str] = None,
    specialized_agents: Optional[Dict[str, Any]] = None
) -> ProductionAgent:
    """Factory function to create a production agent."""
    return ProductionAgent(weights=weights, specialized_agents=specialized_agents)


def create_dual_system(
    researcher_weights: Optional[str] = None,
    production_weights: Optional[str] = None
) -> DualModelSystem:
    """Create a dual model system with researcher and production agents."""
    return DualModelSystem(researcher_weights, production_weights)
