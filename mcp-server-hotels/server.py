from mcp.server.fastmcp import FastMCP
import json

# Create server
mcp = FastMCP("Hotels MCP", stateless_http=True, port=8003)

with open("test_data.json", "r") as f:
    hotels = json.load(f)


@mcp.tool(description="Find hotels matching given criteria")
def find_hotels(
    tags: list[str] = None,
    price_level: str = None,
    location: str = None,
    amenities: list[str] = None,
    room_types: list[str] = None,
    min_rating: float = None
) -> list[dict]:
    """
    Find hotels matching the given criteria.
    All parameters are optional - only filter on provided criteria.
    """
    matches = []
    
    for hotel in hotels:
        # Only check criteria that were provided
        if amenities and not all(amenity in hotel["amenities"] for amenity in amenities):
            continue
            
        matches.append(hotel)
    
    # Always return a list, even if empty
    return matches if matches else []

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

