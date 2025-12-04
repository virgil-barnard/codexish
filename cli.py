"""
cli.py — AutoGen AgentChat GitHub Agent CLI
"""

import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import typer
import requests
from dotenv import load_dotenv

# Correct imports per latest AutoGen AgentChat
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
# from autogen_agentchat.groupchat import GroupChat, GroupChatManager
import autogen_agentchat as agc  # for config loading

load_dotenv()

# Load prompts
DEV_SYSTEM_PROMPT = Path("prompts/dev_agent_system.md").read_text()
REVIEWER_SYSTEM_PROMPT = Path("prompts/reviewer_agent_system.md").read_text()

app = typer.Typer(help="AutoGen AgentChat GitHub CLI")


def run_cmd(cmd, cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        shell=isinstance(cmd, str),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {cmd}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout.strip()


def ensure_clone(repo_url: str, clone_dir: Path) -> Path:
    clone_dir = clone_dir.expanduser().resolve()
    if not clone_dir.exists():
        clone_dir.parent.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "clone", repo_url, str(clone_dir)])
    return clone_dir


def create_work_branch(repo_dir: Path, base_branch: str,
                       prefix: str = "autogen-task-") -> str:
    run_cmd(["git", "fetch", "origin"], cwd=repo_dir)
    run_cmd(["git", "checkout", base_branch], cwd=repo_dir)
    run_cmd(["git", "pull", "origin", base_branch], cwd=repo_dir)
    branch_name = f"{prefix}{uuid.uuid4().hex[:8]}"
    run_cmd(["git", "checkout", "-b", branch_name], cwd=repo_dir)
    return branch_name


def commit_and_push(repo_dir: Path, message: str, branch_name: str) -> bool:
    status = run_cmd(["git", "status", "--short"], cwd=repo_dir)
    if not status.strip():
        return False
    run_cmd(["git", "add", "."], cwd=repo_dir)
    run_cmd(["git", "commit", "-m", message], cwd=repo_dir)
    run_cmd(["git", "push", "-u", "origin", branch_name], cwd=repo_dir)
    return True


def parse_repo_url(repo_url: str):
    if repo_url.startswith("git@github.com:"):
        full = repo_url.replace("git@github.com:", "")
    elif "github.com/" in repo_url:
        full = repo_url.split("github.com/")[1]
    else:
        raise ValueError("Invalid GitHub repo URL")
    if full.endswith(".git"):
        full = full[:-4]
    owner, repo = full.split("/", 1)
    return owner, repo


def fetch_issue(owner: str, repo: str, issue_number: int) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN must be set for --issue")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch issue #{issue_number}: {resp.text}")
    return resp.json()


def create_pull_request(owner: str, repo: str, branch_name: str,
                        base_branch: str, title: str, body: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN must be set for PR creation")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    data = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": base_branch,
        "maintainer_can_modify": True,
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json=data,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create PR: {resp.text}")
    return resp.json().get("html_url", "(no URL returned)")


def get_llm_config():
    # Load LLM config from environment variable (OAI_CONFIG_LIST)
    config_list = agc.config_list_from_json(
        env_or_file="OAI_CONFIG_LIST",
        filter_dict=None,
    )
    if not config_list:
        raise RuntimeError("OAI_CONFIG_LIST missing or empty")
    return {"config_list": config_list}


def run_autogen_workflow(
    repo_dir: Path,
    repo_url: str,
    base_branch: str,
    user_task: str,
    branch_prefix: str = "autogen-task-",
    max_rounds: int = 12,
    issue_number: Optional[int] = None,
):
    branch_name = create_work_branch(repo_dir, base_branch, prefix=branch_prefix)
    typer.echo(f"[+] Branch created: {branch_name}")

    llm_cfg = get_llm_config()
    repo_root = str(repo_dir)

    dev_agent = AssistantAgent(
        name="DevAgent",
        system_message=DEV_SYSTEM_PROMPT,
        llm_config=llm_cfg,
    )
    reviewer_agent = AssistantAgent(
        name="ReviewerAgent",
        system_message=REVIEWER_SYSTEM_PROMPT,
        llm_config=llm_cfg,
    )
    user_proxy = UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        code_execution_config={"work_dir": repo_root, "use_docker": False},
        system_message="You execute Python code to inspect or modify the repo.",
    )

    groupchat = GroupChat(
        agents=[user_proxy, dev_agent, reviewer_agent],
        max_round=max_rounds,
    )
    manager = GroupChatManager(
        name="Manager",
        groupchat=groupchat,
        llm_config=llm_cfg,
    )

    initial_message = f"""
USER TASK:
{user_task}

WORKFLOW:
- DevAgent inspects files, proposes changes.
- DevAgent uses UserProxy to execute Python code (read/write files, run tests).
- ReviewerAgent requests modifications or approves.
- Final output must include: FINAL REVIEW: APPROVED
    """

    user_proxy.initiate_chat(manager, message=initial_message)

    typer.echo("[+] Attempting commit & push...")
    changed = commit_and_push(repo_dir,
                              f"Autogen: {user_task[:60]}",
                              branch_name)
    if not changed:
        typer.echo("[=] No changes to commit.")
        return

    typer.echo(f"[+] Branch pushed: {branch_name}")

    owner, repo = parse_repo_url(repo_url)
    if issue_number:
        title = f"[AutoGen] Resolve Issue #{issue_number}: {user_task.splitlines()[0]}"
        body = f"This PR was autogenerated.\n\nCloses #{issue_number}.\n"
    else:
        title = f"[AutoGen] {user_task.splitlines()[0][:60]}"
        body = "This PR was autogenerated by AutoGen.\n"

    pr_url = create_pull_request(owner, repo, branch_name, base_branch, title, body)
    typer.echo(f"[+] PR created: {pr_url}")


@app.command()
def run(
    repo_url: str = typer.Option(..., "--repo-url"),
    base_branch: str = typer.Option("main", "--base-branch"),
    task: Optional[str] = typer.Option(None, "--task"),
    issue: Optional[int] = typer.Option(None, "--issue"),
    clone_dir: Path = typer.Option(Path("./repo_cache"), "--clone-dir"),
    branch_prefix: str = typer.Option("autogen-task-", "--branch-prefix"),
    max_rounds: int = typer.Option(12, "--max-rounds"),
):
    if not task and not issue:
        raise typer.BadParameter("You must provide --task or --issue")

    owner, repo_name = parse_repo_url(repo_url)

    if issue:
        typer.echo(f"[+] Loading GitHub Issue #{issue}...")
        issue_data = fetch_issue(owner, repo_name, issue)
        title = issue_data.get("title", "")
        body = issue_data.get("body", "")
        task = f"{title}\n\n{body}"
        typer.echo("[+] Issue loaded.")

    repo_dir = ensure_clone(repo_url, clone_dir)
    typer.echo(f"[+] Repo directory: {repo_dir}")

    run_autogen_workflow(
        repo_dir=repo_dir,
        repo_url=repo_url,
        base_branch=base_branch,
        user_task=task,
        branch_prefix=branch_prefix,
        max_rounds=max_rounds,
        issue_number=issue,
    )


if __name__ == "__main__":
    app()