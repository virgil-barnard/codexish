import os
import sys
import asyncio
import json
import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_URL = os.getenv("REPO_URL")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# ------------------------------------------------------------
# GitHub tools
# ------------------------------------------------------------

@tool
def github_list_repos() -> str:
    """Lists the authenticated user's repositories on GitHub."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    url = "https://api.github.com/user/repos"

    r = httpx.get(url, headers=headers)
    if r.status_code != 200:
        return f"Error: {r.status_code} {r.text}"

    repos = [repo["full_name"] for repo in r.json()]
    return "\n".join(repos)

@tool
def github_create_issue(title: str, body: str = "") -> str:
    """Creates an issue in the repository specified by REPO_URL."""
    if not REPO_URL:
        return "REPO_URL not set"

    match = REPO_URL.strip().split(":")[-1].replace(".git", "")
    owner, repo = match.split("/")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {"title": title, "body": body}

    r = httpx.post(url, headers=headers, json=data)
    if r.status_code != 201:
        return f"Failed to create issue: {r.status_code} {r.text}"
    return f"Issue created at: {r.json().get('html_url')}"

# ------------------------------------------------------------
# Langchain agent
# ------------------------------------------------------------

async def run_agent():
    llm = ChatOpenAI(model=MODEL, temperature=0)

    tools = [
        Tool.from_function(github_list_repos),
        Tool.from_function(github_create_issue),
    ]

    agent = initialize_agent(
        tools=tools,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        llm=llm,
        verbose=True
    )

    response = agent.run(
        "List my GitHub repositories and then create a test issue "
        "in the repo from REPO_URL titled 'Langchain Issue' with a short body."
    )

    print("\n=== Final Output ===\n", response)

# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_agent())
