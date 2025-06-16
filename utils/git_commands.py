#!/usr/bin/env python3

import subprocess
import shlex
from typing import List

def run_git_command(command: List[str]) -> str:
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
    return run_git_command(["status"])

def get_git_branch() -> str:
    return run_git_command(["branch"])

def get_git_remote_branches() -> str:
    return run_git_command(["branch", "-r"])

def get_git_log(num_entries: int = 5) -> str:
    return run_git_command(["log", f"-{num_entries}", "--oneline"])

def get_git_diff() -> str:
    return run_git_command(["diff", "--stat"])

def get_git_unpushed_commits() -> str:
    try:
        current_branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return run_git_command(["log", f"@{{u}}..{current_branch}", "--oneline"])
    except:
        return "Unable to determine unpushed commits."

def get_remotes() -> str:
    return run_git_command(["remote", "-v"])

def execute_git_command(command: str) -> str:
    """Execute a git command, properly handling quoted arguments."""
    try:
        # Remove git prefix if present
        if command.startswith("git "):
            command = command[4:]
        
        # Use shlex to properly parse quoted arguments
        parts = shlex.split(command)
        
        print(f"🔧 Executing git command parts: {parts}")
        return run_git_command(parts)
    except ValueError as e:
        # Fallback to simple split if shlex fails
        print(f"⚠️ shlex parsing failed: {e}, using simple split")
        parts = command.split()
        if parts and parts[0] == "git":
            parts = parts[1:]
        return run_git_command(parts) 