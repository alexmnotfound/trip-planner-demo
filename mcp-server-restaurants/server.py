from mcp.server.fastmcp import FastMCP
import json

# Create server
mcp = FastMCP("Restaurants MCP", stateless_http=True, port=8002)

with open("test_data.json", "r") as f:
    restaurants = json.load(f)


@mcp.tool(description="Find restaurants matching given criteria")
def find_restaurants(
    tags: list[str] = None,
    price_level: str = None,
    location: str = None,
    cuisine: str = None,
    dietary_options: list[str] = None
) -> list[dict]:
    """
    Find restaurants matching the given criteria.
    All parameters are optional - only filter on provided criteria.
    """
    matches = []
    print(dietary_options)
    print(restaurants)
    for restaurant in restaurants:
        # Only check criteria that were provided
        if dietary_options and not all(opt in restaurant["dietary_options"] for opt in dietary_options):
            continue
            
        matches.append(restaurant)
    
    # Always return a list, even if empty
    return matches if matches else []

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

