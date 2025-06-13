from mcp.server.fastmcp import FastMCP

# Create server
mcp = FastMCP("Echo Server", stateless_http=True)


@mcp.tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
