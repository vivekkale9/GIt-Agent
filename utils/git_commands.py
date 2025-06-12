#!/usr/bin/env python3

import subprocess
from typing import List

def run_git_command(command: List[str]) -> str:
    """Run a git command and return its output."""
    try:
        result = subprocess.run(
            ["git"] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

def get_git_status() -> str:
    """Get the current git status."""
    return run_git_command(["status"])

def get_git_branch() -> str:
    """Get the current git branch."""
    return run_git_command(["branch"])

def get_git_remote_branches() -> str:
    """Get remote branches."""
    return run_git_command(["branch", "-r"])

def get_git_log(num_entries: int = 5) -> str:
    """Get the recent git log entries."""
    return run_git_command(["log", f"-{num_entries}", "--oneline"])

def get_git_diff() -> str:
    """Get git diff of current changes."""
    return run_git_command(["diff", "--stat"])

def get_git_unpushed_commits() -> str:
    """Get unpushed commits."""
    try:
        current_branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return run_git_command(["log", f"@{{u}}..{current_branch}", "--oneline"])
    except:
        return "Unable to determine unpushed commits."

def get_remotes() -> str:
    """Get configured remotes."""
    return run_git_command(["remote", "-v"])

def execute_git_command(command: str) -> str:
    """Execute a custom git command."""
    parts = command.split()
    if parts and parts[0] == "git":
        parts = parts[1:]
    return run_git_command(parts) 