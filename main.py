import asyncio
import os
from dotenv import load_dotenv
from agents import Agent, Runner
from openai import OpenAI

# Load env vars
load_dotenv()

async def main():

    # Create agent
    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
    )

    # Run agent
    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())