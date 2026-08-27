"""
News Agent - Specialized Needle agent for news queries.
Provides tool-calling interface for news data retrieval and summarization.
"""

import needle
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NewsArticle(BaseModel):
    """Structured news article."""
    title: str
    source: str
    category: str
    summary: str
    published_at: Optional[str] = None
    url: Optional[str] = None


class NewsSummary(BaseModel):
    """Summary of news on a topic."""
    topic: str
    num_articles: int
    key_points: List[str]
    sources: List[str]


# Tool functions for news domain
@needle.tool
def get_news(topic: str, category: Optional[str] = None, limit: int = 5) -> List[NewsArticle]:
    """Get news articles on a specific topic.
    
    Args:
        topic: News topic or keyword
        category: Filter by category (politics, technology, sports, etc.)
        limit: Maximum number of articles to return
    
    Returns:
        List of NewsArticle objects
    """
    # Mock news data
    mock_news = {
        "technology": [
            NewsArticle(
                title="AI Breakthrough in Medical Diagnosis",
                source="Tech Daily",
                category="technology",
                summary="Researchers have developed a new AI model that can diagnose diseases from medical images with 95% accuracy.",
                published_at="2026-08-25T10:00:00Z"
            ),
            NewsArticle(
                title="New Smartphone Released with Revolutionary Features",
                source="Gadget News",
                category="technology",
                summary="TechCorp announces its latest smartphone with holographic display and AI-powered camera.",
                published_at="2026-08-24T14:30:00Z"
            ),
        ],
        "politics": [
            NewsArticle(
                title="International Climate Agreement Signed",
                source="Global Times",
                category="politics",
                summary="World leaders have signed a historic agreement to reduce carbon emissions by 50% by 2040.",
                published_at="2026-08-26T08:00:00Z"
            ),
        ],
        "sports": [
            NewsArticle(
                title="Olympic Games Begin with Record Attendance",
                source="Sports Illustrated",
                category="sports",
                summary="The 2026 Olympic Games have officially begun with record-breaking viewership worldwide.",
                published_at="2026-08-25T18:00:00Z"
            ),
        ],
    }
    
    # Filter by category
    if category:
        articles = mock_news.get(category.lower(), [])
    else:
        articles = [article for category_articles in mock_news.values() for article in category_articles]
    
    # Filter by topic (simple keyword match)
    filtered = [a for a in articles if topic.lower() in a.title.lower() or topic.lower() in a.summary.lower()]
    
    return filtered[:limit]


@needle.tool
def summarize_topic(topic: str, num_articles: int = 10) -> NewsSummary:
    """Get a summary of news on a topic.
    
    Args:
        topic: News topic
        num_articles: Number of articles to analyze
    
    Returns:
        NewsSummary with key points and sources
    """
    articles = get_news(topic, limit=num_articles)
    
    key_points = []
    sources = list(set(a.source for a in articles))
    
    for article in articles[:5]:  # Top 5 articles
        key_points.append(article.summary)
    
    return NewsSummary(
        topic=topic,
        num_articles=len(articles),
        key_points=key_points,
        sources=sources
    )


@needle.tool
def get_categories() -> List[str]:
    """Get available news categories.
    
    Returns:
        List of news category names
    """
    return ["technology", "politics", "sports", "business", "health", "entertainment", "science"]


# Available tools for news agent
NEWS_TOOLS = [get_news, summarize_topic, get_categories]


class NewsAgent:
    """Specialized news agent using Needle."""
    
    def __init__(self, weights: str = None):
        """Initialize news agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
        """
        self.agent = needle.Needle(
            tools=NEWS_TOOLS,
            weights=weights,
            system="You are a news assistant. Provide accurate, up-to-date news information. "
                   "Summarize articles and provide key insights on requested topics."
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the news agent on a query."""
        return self.agent.run(query, max_steps=max_steps)
    
    def get_tools_schema(self) -> list:
        """Get JSON schemas for all news tools."""
        return [needle.agent.tools.build_schema(tool) for tool in NEWS_TOOLS]
