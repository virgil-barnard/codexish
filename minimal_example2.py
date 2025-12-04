import os
import sys
import asyncio
import json
import httpx
from dotenv import load_dotenv

from langchain_core.tools import Tool
# from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI   
from langchain.agents import create_openai_functions_agent
from langchain.agents.agent import AgentExecutor

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_URL = os.getenv("REPO_URL")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


@tool
def github_list_repos() -> str:
    """Lists the authenticated user's repositories on GitHub."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    r = httpx.get("https://api.github.com/user/repos", headers=headers)
    if r.status_code != 200:
        return f"Error: {r.status_code} {r.text}"
    return "\n".join([repo["full_name"] for repo in r.json()])


@tool
def github_create_issue(title: str, body: str = "") -> str:
    """Creates an issue in the repository specified by REPO_URL."""
    if not REPO_URL:
        return "REPO_URL not set"

    repo_path = REPO_URL.split(":")[-1].replace(".git", "")
    owner, repo = repo_path.split("/")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    payload = {"title": title, "body": body}

    r = httpx.post(url, headers=headers, json=payload)
    if r.status_code != 201:
        return f"Failed to create issue: {r.status_code} {r.text}"

    return f"Issue created: {r.json()['html_url']}"


async def run_agent():
    llm = ChatOpenAI(model=MODEL, temperature=0)  

    tools = [
        Tool.from_function(github_list_repos),
        Tool.from_function(github_create_issue),
    ]

    agent = create_openai_functions_agent(llm=llm, tools=tools)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    result = await executor.ainvoke(
        {
            "input": "List my repositories and create an issue titled 'LangChain Test Issue'."
        }
    )

    print("\n=== Final ===\n", result)


if __name__ == "__main__":
    asyncio.run(run_agent())
