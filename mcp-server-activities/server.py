from mcp.server.fastmcp import FastMCP
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create server
mcp = FastMCP("Activities MCP", stateless_http=True, port=8004)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@mcp.tool(description="Get personalized activity recommendations based on user profile and location")
def get_activities(
    location: str,
    interests: list[str] = None,
    mobility: str = None,
    budget: str = None
) -> list[dict]:
    """
    Get personalized activity recommendations for a location based on user preferences.
    Uses OpenAI to generate relevant and personalized suggestions.
    """
    try:
        # Construct the prompt for OpenAI
        prompt = f"""Given the following user preferences, suggest 5 best activities to do in {location}:
        - Interests: {', '.join(interests) if interests else 'Not specified'}
        - Mobility level: {mobility if mobility else 'Not specified'}
        - Budget: {budget if budget else 'Not specified'}
        
        For each activity, provide:
        1. Name
        2. Brief description
        3. Why it matches the user's preferences
        4. Estimated duration
        5. Estimated cost range
        
        Format the response as a JSON array of objects with these fields:
        - name
        - description
        - match_reason
        - duration
        - cost_range
        """

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a travel expert that provides personalized activity recommendations."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # Parse the response
        activities = json.loads(response.choices[0].message.content)
        return activities.get("activities", [])

    except Exception as e:
        print(f"Error generating activities: {str(e)}")
        return []

if __name__ == "__main__":
    mcp.run(transport="streamable-http") 