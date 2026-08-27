"""
Weather Agent - Specialized Needle agent for weather queries.
Provides tool-calling interface for weather data retrieval.
"""

import needle
from pydantic import BaseModel
from typing import Optional


class WeatherData(BaseModel):
    """Structured weather response."""
    city: str
    temperature_c: float
    temperature_f: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    condition: str
    units: str = "metric"


# Tool functions for weather domain
@needle.tool
def get_weather(city: str, units: str = "metric") -> WeatherData:
    """Get current weather for a city.
    
    Args:
        city: City name to query
        units: 'metric' for Celsius, 'imperial' for Fahrenheit
    
    Returns:
        WeatherData with temperature, humidity, wind, and condition
    """
    # TODO: Replace with actual API call or database query
    # This is a mock implementation
    mock_data = {
        "Lagos": {"temp_c": 28.5, "humidity": 75, "wind": 12.3, "condition": "partly cloudy"},
        "New York": {"temp_c": 22.1, "humidity": 65, "wind": 8.5, "condition": "sunny"},
        "Tokyo": {"temp_c": 25.8, "humidity": 80, "wind": 5.2, "condition": "rainy"},
        "London": {"temp_c": 18.3, "humidity": 70, "wind": 15.0, "condition": "overcast"},
    }
    
    city_lower = city.lower()
    for key, data in mock_data.items():
        if key.lower() in city_lower:
            weather = data
            break
    else:
        weather = mock_data["Lagos"]  # Default
    
    temp_f = weather["temp_c"] * 9/5 + 32 if units == "imperial" else None
    
    return WeatherData(
        city=city,
        temperature_c=weather["temp_c"],
        temperature_f=temp_f,
        humidity=weather["humidity"],
        wind_speed=weather["wind"],
        condition=weather["condition"],
        units=units
    )


@needle.tool
def get_forecast(city: str, days: int = 3) -> list:
    """Get weather forecast for a city.
    
    Args:
        city: City name
        days: Number of days to forecast (1-7)
    
    Returns:
        List of forecast entries with date, high, low, condition
    """
    # Mock forecast data
    forecast = []
    for i in range(min(days, 7)):
        forecast.append({
            "date": f"2026-08-{26+i}",
            "high_c": 28 + (i * 0.5),
            "low_c": 22 + (i * 0.3),
            "condition": ["sunny", "partly cloudy", "rainy", "overcast"][i % 4]
        })
    return forecast


@needle.tool
def search_city(query: str) -> list:
    """Search for cities matching a query.
    
    Args:
        query: Partial or full city name
    
    Returns:
        List of matching city names
    """
    cities = ["Lagos", "New York", "Tokyo", "London", "Paris", "Berlin", 
              "Sydney", "Toronto", "Mumbai", "Singapore"]
    return [c for c in cities if query.lower() in c.lower()]


# Available tools for weather agent
WEATHER_TOOLS = [get_weather, get_forecast, search_city]


class WeatherAgent:
    """Specialized weather agent using Needle."""
    
    def __init__(self, weights: str = None):
        """Initialize weather agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
        """
        self.agent = needle.Needle(
            tools=WEATHER_TOOLS,
            weights=weights,
            system="You are a weather assistant. Provide accurate weather information. "
                   "Use tools to get current conditions and forecasts."
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the weather agent on a query.
        
        Args:
            query: User query about weather
            max_steps: Maximum tool-calling iterations
        
        Returns:
            Response dictionary with results
        """
        return self.agent.run(query, max_steps=max_steps)
    
    def get_tools_schema(self) -> list:
        """Get JSON schemas for all weather tools."""
        return needle.agent.tools.build_schema(tool) for tool in WEATHER_TOOLS
