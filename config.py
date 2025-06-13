# MCP Server Configuration
MCP_SERVERS = {
    "Restaurants MCP": "http://127.0.0.1:8002/mcp",
    "Hotels MCP": "http://127.0.0.1:8003/mcp",
}

# User Profiles
USER_PROFILES = [
    {
        "name": "Sofia",
        "budget": "mid-range",
        "food_preferences": ["local", "vegetarian"],
        "mobility": "low",
        "interests": ["quiet places", "walkable cities"],
        "location": "Paris"
    },
    {
        "name": "Alex",
        "budget": "luxury",
        "food_preferences": ["fine dining", "seafood"],
        "mobility": "high",
        "interests": ["beachfront", "water activities"],
        "location": "New York"
    }
]

# Agent Configuration
AGENT_CONFIG = {
    "name": "Trip Planner Agent",
    "instructions": """
    You are a trip planner assistant that helps recommend the best accommodations and dining options for specific travelers.
    You are provided with a user profile that includes preferences, constraints, and past travel behavior.
    You have access to two tools via the MCP protocol:
    - hotel_tool: returns a list of available hotels based on location and user preferences
    - restaurant_tool: returns a list of restaurants based on location and user preferences

    Your job is to:
    1. Call both MCP tools using the user profile and target location
    2. Evaluate the returned items using the profile's tags (e.g. "budget": "mid-range", "diet": "vegetarian", "mobility": "low")
    3. Return the top 3 hotels and top 3 restaurants that best match the user
    4. For each recommendation, include a clear explanation of why it was selected based on the profile

    Return your recommendations in this JSON format:
    {
        "hotels": [
            {
                "name": "Hotel Name",
                "description": "Hotel description",
                "reason": "Explanation of why this hotel matches the user's profile"
            }
        ],
        "restaurants": [
            {
                "name": "Restaurant Name",
                "description": "Restaurant description",
                "reason": "Explanation of why this restaurant matches the user's profile"
            }
        ]
    }

    Constraints:
    - Do not recommend places that contradict the user's constraints
    - Prioritize matches on tags (price range, dietary needs, interests)
    - If multiple options are similarly good, use past travel behavior or diversity to choose""",
    "model_settings": {
        "tool_choice": "required"
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
} 