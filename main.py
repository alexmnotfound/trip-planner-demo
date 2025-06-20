import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from agents import Agent, Runner
from agents.model_settings import ModelSettings
from typing import Dict, List, Tuple
import sys
import logging
from contextlib import asynccontextmanager
from config import MCP_SERVERS, AGENT_CONFIG, USER_PROFILES, LOGGING_CONFIG
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    datefmt=LOGGING_CONFIG["date_format"]
)
logger = logging.getLogger(__name__)
# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

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
        self._cleanup_lock = asyncio.Lock()
        self._cleanup_event = asyncio.Event()

    async def connect(self):
        try:
            logger.info(f"Connecting to {self.name}...")
            
            # Create and enter client context
            self._client_cm = streamablehttp_client(self.url)
            self.client = await self._client_cm.__aenter__()
            read, write, get_session_id = self.client
            
            # Create and enter session context
            self._session_cm = ClientSession(read, write)
            self.session = await self._session_cm.__aenter__()
            
            # Test the connection
            tools = await self.session.list_tools()
            logger.info(f"Connected to {self.name}")
            
            self.named_session = NamedSession(self.session, name=self.name)
            
            # Start keep-alive task
            self.keep_alive_task = asyncio.create_task(self._keep_alive())
            return self.named_session
            
        except Exception as e:
            logger.error(f"Could not connect to {self.name}: {str(e)}")
            await self.cleanup()
            raise

    async def _keep_alive(self):
        try:
            while not self._cleanup_event.is_set():
                await asyncio.sleep(1)
                try:
                    await self.session.list_tools()
                except Exception as e:
                    if not isinstance(e, asyncio.CancelledError):
                        logger.error(f"Keep-alive error for {self.name}: {str(e)}")
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup_event.set()

    async def cleanup(self):
        async with self._cleanup_lock:
            if not self._cleanup_event.is_set():
                self._cleanup_event.set()
                
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
                        if not isinstance(e, (asyncio.CancelledError, RuntimeError)):
                            logger.error(f"Error cleaning up session for {self.name}: {str(e)}")
                
                if self._client_cm:
                    try:
                        await self._client_cm.__aexit__(None, None, None)
                    except Exception as e:
                        if not isinstance(e, (asyncio.CancelledError, RuntimeError)):
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
                    result = await attr(*args, **kwargs)
                    if hasattr(result, "tools"):
                        return result.tools
                    return result
                except Exception as e:
                    logger.error(f"Error in {self.name}.{item}: {str(e)}")
                    raise
            return wrapped
        return attr

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
            except Exception as e:
                logger.error(f"Failed to connect to {name}: {str(e)}")
        
        if not mcp_sessions:
            logger.error("Could not connect to any MCP servers. Exiting.")
            sys.exit(1)
        
        logger.info(f"Connected to {len(mcp_sessions)} MCP servers")
        
        # Create the agent
        agent = Agent(
            name=AGENT_CONFIG["name"],
            instructions=AGENT_CONFIG["instructions"],
            mcp_servers=mcp_sessions,
            model_settings=ModelSettings(**AGENT_CONFIG["model_settings"]),
        )
        
        # Process each user profile
        for profile in USER_PROFILES:
            try:
                logger.info(f"Processing recommendations for user: {profile['name']}")
                # Convert profile to JSON string for the agent
                profile_json = json.dumps(profile)
                result = await Runner.run(starting_agent=agent, input=profile_json)
                
                if not result.final_output:
                    logger.error(f"No recommendations found for {profile['name']}. This may be due to no available tools.")
                else:
                    try:
                        # Try to parse the response as JSON
                        recommendations = json.loads(result.final_output)
                        
                        # Validate the JSON structure
                        required_sections = ["hotels", "restaurants", "activities"]
                        for section in required_sections:
                            if section not in recommendations:
                                recommendations[section] = []
                            elif not isinstance(recommendations[section], list):
                                recommendations[section] = []
                        
                        # Pretty print the recommendations
                        logger.info(f"Recommendations for {profile['name']}:")
                        logger.info(json.dumps(recommendations, indent=2))
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON response for {profile['name']}: {result.final_output}")
                        logger.error("The agent did not return a valid JSON response. Please check the agent's instructions.")
            except Exception as e:
                logger.error(f"Failed to process profile for {profile['name']}: {str(e)}", exc_info=True)
                logger.error("This may be due to no available tools from the connected MCP servers.")
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up all connections
        cleanup_tasks = [connection.cleanup() for connection in connections]
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                if not isinstance(e, asyncio.CancelledError):
                    logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except asyncio.CancelledError:
        # Suppress final CancelledError on shutdown
        pass
    except Exception as e:
        logger.error(f"Program failed: {str(e)}", exc_info=True)
        sys.exit(1)