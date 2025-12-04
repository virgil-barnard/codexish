# minimal_example.py
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Create a model client using your OpenAI key & any model
    client = OpenAIChatCompletionClient(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )

    agent = AssistantAgent(
        name="assistant",
        model_client=client,
    )

    # Ask a simple question
    result = await agent.run(task="Say 'Hello world!' and nothing else.")
    print("Agent response:", result)

if __name__ == "__main__":
    asyncio.run(main())
