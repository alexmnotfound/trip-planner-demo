import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from agents import Agent, Runner
from agents.model_settings import ModelSettings

class NamedSession:
    def __init__(self, session, name="MCP ClientSession"):
        self._session = session
        self.name = name
    def __getattr__(self, item):
        attr = getattr(self._session, item)
        if asyncio.iscoroutinefunction(attr):
            async def wrapped(*args, **kwargs):
                result = await attr(*args, **kwargs)
                if hasattr(result, "tools"):
                    return result.tools
                return result
            return wrapped
        return attr

async def main():
    url = "http://127.0.0.1:8000/mcp"
    async with streamablehttp_client(url) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            named_session = NamedSession(session)
            agent = Agent(
                name="Assistant",
                instructions="Use the tools to answer the questions.",
                mcp_servers=[named_session],
                model_settings=ModelSettings(tool_choice="required"),
            )
            message = "Add these numbers: 21 and 21."
            print(f"Running: {message}")
            result = await Runner.run(starting_agent=agent, input=message)
            print("Result from agent:", result.final_output)

if __name__ == "__main__":
    asyncio.run(main())