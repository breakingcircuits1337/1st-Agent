"""
Agent modules for 1st Agent framework.
Each agent is a specialized Needle instance with domain-specific tools.
"""

from .weather_agent import WeatherAgent
from .news_agent import NewsAgent
from .db_agent import DBAgent

__all__ = ["WeatherAgent", "NewsAgent", "DBAgent"]
