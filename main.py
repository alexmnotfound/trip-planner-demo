import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from agents import Agent, Runner
from agents.model_settings import ModelSettings
from typing import Dict, List, Tuple
import sys
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPConnection:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.client = None
        self.session = None
        self.named_session = None
        self.keep_alive_task = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self):
        try:
            logger.info(f"Attempting to connect to {self.name} at {self.url}")
            
            # Create and enter client context
            self._client_cm = streamablehttp_client(self.url)
            self.client = await self._client_cm.__aenter__()
            read, write, get_session_id = self.client
            
            # Create and enter session context
            self._session_cm = ClientSession(read, write)
            self.session = await self._session_cm.__aenter__()
            
            # Test the connection
            tools = await self.session.list_tools()
            logger.info(f"Successfully connected to {self.name}. Available tools: {tools}")
            
            self.named_session = NamedSession(self.session, name=self.name)
            logger.info(f"Created NamedSession for {self.name}")
            
            # Start keep-alive task
            self.keep_alive_task = asyncio.create_task(self._keep_alive())
            return self.named_session
            
        except Exception as e:
            logger.error(f"Could not connect to MCP server '{self.name}' at {self.url}: {str(e)}")
            await self.cleanup()
            raise

    async def _keep_alive(self):
        try:
            while True:
                await asyncio.sleep(1)
                try:
                    await self.session.list_tools()
                except Exception as e:
                    logger.error(f"Error in keep_alive for {self.name}: {str(e)}")
                    break
        except asyncio.CancelledError:
            logger.info(f"Keep alive task cancelled for {self.name}")
            raise

    async def cleanup(self):
        if self.keep_alive_task and not self.keep_alive_task.done():
            self.keep_alive_task.cancel()
            try:
                await self.keep_alive_task
            except asyncio.CancelledError:
                pass
        
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up session for {self.name}: {str(e)}")
        
        if self._client_cm:
            try:
                await self._client_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up client for {self.name}: {str(e)}")

class NamedSession:
    def __init__(self, session, name="MCP ClientSession"):
        self._session = session
        self.name = name
        
    def __getattr__(self, item):
        attr = getattr(self._session, item)
        if asyncio.iscoroutinefunction(attr):
            async def wrapped(*args, **kwargs):
                try:
                    logger.debug(f"Calling {item} on {self.name} with args: {args}, kwargs: {kwargs}")
                    result = await attr(*args, **kwargs)
                    if hasattr(result, "tools"):
                        logger.debug(f"Got tools from {self.name}: {result.tools}")
                        return result.tools
                    return result
                except Exception as e:
                    logger.error(f"Error in {self.name}.{item}: {str(e)}")
                    raise
            return wrapped
        return attr

# Configuration for MCP servers
MCP_SERVERS = {
    "Restaurants MCP": "http://127.0.0.1:8002/mcp",
    "Hotels MCP": "http://127.0.0.1:8003/mcp",
    # Add more MCPs here as needed
    # "Activities MCP": "http://127.0.0.1:8004/mcp",
    # "Transportation MCP": "http://127.0.0.1:8005/mcp",
}

async def main():
    connections = []
    try:
        # Create and maintain sessions for all MCP servers
        mcp_sessions = []
        
        for name, url in MCP_SERVERS.items():
            try:
                connection = MCPConnection(name, url)
                session = await connection.connect()
                connections.append(connection)
                mcp_sessions.append(session)
                logger.info(f"Connected to {name}")
            except Exception as e:
                logger.error(f"Failed to establish session for {name}: {str(e)}")
        
        if not mcp_sessions:
            logger.error("Could not connect to any MCP servers. Exiting.")
            sys.exit(1)
        
        logger.info(f"Connected to {len(mcp_sessions)} MCP servers")
        
        try:
            # Create and run the agent
            agent = Agent(
                name="Assistant",
                instructions="Use the tools to answer the questions.",
                mcp_servers=mcp_sessions,
                model_settings=ModelSettings(tool_choice="required"),
            )
            
            message = "Find me a hotel that has a pool and a restaurant that has vegetarian options."
            logger.info(f"Running query: {message}")
            
            result = await Runner.run(starting_agent=agent, input=message)
            if not result.final_output:
                logger.error("No result from agent. This may be due to no available tools.")
            else:
                logger.info("Result from agent: %s", result.final_output)
        except Exception as e:
            logger.error(f"Agent run failed: {str(e)}", exc_info=True)
            logger.error("This may be due to no available tools from the connected MCP servers.")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up all connections
        for connection in connections:
            await connection.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program failed: {str(e)}", exc_info=True)
        sys.exit(1)