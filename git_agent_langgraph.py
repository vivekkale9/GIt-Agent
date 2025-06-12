#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import json
from typing import Dict, List, Any, Annotated, TypedDict, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.llms.ollama import Ollama
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Git command helpers
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

def get_git_log(num_entries: int = 5) -> str:
    """Get the recent git log entries."""
    return run_git_command(["log", f"-{num_entries}", "--oneline"])

def get_git_diff() -> str:
    """Get git diff of current changes."""
    return run_git_command(["diff", "--stat"])

def execute_git_command(command: List[str]) -> str:
    """Execute a custom git command."""
    return run_git_command(command)

def get_git_remote_branches() -> str:
    """Get remote branches."""
    return run_git_command(["branch", "-r"])

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

# Define our state and action models
class GitAction(TypedDict):
    action_type: Literal["execute_command", "provide_info", "end"]
    command: str
    reasoning: str

class GitAgentState(TypedDict):
    query: str
    status: str
    branches: str
    recent_commits: str
    diff_stat: str
    remote_branches: str
    unpushed_commits: str
    remotes: str
    history: List[Dict[str, Any]]
    action: GitAction
    response: str
    execution_stopped: bool

# Graph nodes
def analyzer(state: GitAgentState) -> GitAgentState:
    """Analyze the repository and decide what action to take."""
    llm = Ollama(model="llama2")
    
    prompt = ChatPromptTemplate.from_template("""
    You are GitAgent, an AI assistant specialized in Git operations.
    Analyze the Git repository information provided and respond to the user's request.
    
    Git repository information:
    - Status: {status}
    - Current branches: {branches}
    - Recent commits: {recent_commits}
    - Current changes: {diff_stat}
    
    User query: {query}
    
    First, determine what type of action is needed.
    
    If the user wants to perform Git operations like merging, rebasing, pushing, pulling, etc., you should:
    1. Select "execute_command" as the action_type
    2. Include the FIRST command that needs to be run in the "command" field
    3. Provide detailed reasoning for this step in "reasoning" field, including what subsequent steps will be needed
    
    Return your response as a JSON object with the following structure:
    {
        "action_type": "execute_command" | "provide_info" | "end",
        "command": "the git command to execute (if applicable)",
        "reasoning": "your reasoning for this action, including any additional steps that will be needed"
    }
    
    Be proactive - if a task requires multiple Git commands to complete (like merging branches),
    plan out all the steps, but only put the first command in the "command" field. You'll handle
    subsequent commands in later iterations.
    """)
    
    chain = prompt | llm | JsonOutputParser()
    
    action = chain.invoke({
        "status": state["status"],
        "branches": state["branches"],
        "recent_commits": state["recent_commits"],
        "diff_stat": state["diff_stat"],
        "query": state["query"],
    })
    
    state["action"] = action
    # Add to history
    state["history"].append({"action": action, "state": "analyzer"})
    
    return state

def command_executor(state: GitAgentState) -> GitAgentState:
    """Execute the recommended Git command."""
    action = state["action"]
    
    if action["action_type"] != "execute_command" or not action["command"]:
        return state
    
    # Clean up the command
    command = action["command"]
    if command.startswith("git "):
        command = command[4:]
    
    # Check for auto-approve from command line args
    auto_approve = False
    for arg in sys.argv:
        if arg == "--auto-approve" or arg == "-y":
            auto_approve = True
            break
    
    # If not auto-approved, ask for confirmation
    if not auto_approve:
        print(f"\n🔍 Recommended Git command: git {command}")
        print(f"📝 Reasoning: {action['reasoning']}")
        confirmation = input("\nDo you want to execute this command? (yes/no): ").lower()
        if confirmation not in ["yes", "y"]:
            print("Command execution skipped.")
            state["execution_stopped"] = True
            return state
    
    # Execute the command
    print(f"\n🚀 Executing: git {command}")
    result = execute_git_command(command.split())
    
    # Update state with execution results
    state["response"] = f"Command executed: git {command}\nResult:\n{result}"
    
    # Add to history
    state["history"].append({"action": action, "result": result, "state": "command_executor"})
    
    # After executing, refresh repository info
    state["status"] = get_git_status()
    state["branches"] = get_git_branch()
    state["recent_commits"] = get_git_log()
    state["diff_stat"] = get_git_diff()
    state["remote_branches"] = get_git_remote_branches()
    state["unpushed_commits"] = get_git_unpushed_commits()
    state["remotes"] = get_remotes()
    
    # Check for errors or conflicts
    if "error" in result.lower() or "conflict" in result.lower():
        print("\n⚠️ There might be an issue with the command execution.")
        continue_execution = input("Do you want to continue with the next steps? (yes/no): ").lower()
        if continue_execution not in ["yes", "y"]:
            print("Workflow execution stopped.")
            # Add this information to the state
            state["execution_stopped"] = True
    
    return state

def info_provider(state: GitAgentState) -> GitAgentState:
    """Provide information without executing commands."""
    llm = Ollama(model="llama2")
    
    prompt = ChatPromptTemplate.from_template("""
    You are GitAgent, an AI assistant specialized in Git operations.
    Based on the Git repository information, provide a helpful response to the user's query.
    
    Git repository information:
    - Status: {status}
    - Current branches: {branches}
    - Recent commits: {recent_commits}
    - Current changes: {diff_stat}
    
    User query: {query}
    
    Your reasoning: {reasoning}
    
    Provide a clear and concise answer to the user's question. Include specific details from 
    the repository information provided above. If relevant, suggest Git commands that 
    the user could run, but format them clearly as suggestions, not as commands to be executed.
    """)
    
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "status": state["status"],
        "branches": state["branches"],
        "recent_commits": state["recent_commits"],
        "diff_stat": state["diff_stat"],
        "query": state["query"],
        "reasoning": state["action"]["reasoning"]
    })
    
    state["response"] = response
    
    # Add to history
    state["history"].append({"response": response, "state": "info_provider"})
    
    return state

def responder(state: GitAgentState) -> GitAgentState:
    """Generate a final response based on the actions taken."""
    llm = Ollama(model="llama2")
    
    # Prepare history for context
    history_text = ""
    for entry in state["history"]:
        if "state" in entry:
            if entry["state"] == "command_executor" and "result" in entry:
                history_text += f"Executed: git {entry['action']['command']}\nResult: {entry['result']}\n\n"
    
    prompt = ChatPromptTemplate.from_template("""
    You are GitAgent, an AI assistant specialized in Git operations.
    Based on all information gathered and actions taken, provide a final response to the user's query.
    
    Current Git repository information:
    - Status: {status}
    - Current branches: {branches}
    - Recent commits: {recent_commits}
    - Current changes: {diff_stat}
    
    User query: {query}
    
    Actions taken:
    {history}
    
    Provide a clear, helpful, and comprehensive final response to the user's query.
    Include explanations of what was done, what was found, and any additional recommendations.
    
    If the workflow was completed successfully, summarize the changes made.
    If there were any issues, explain what might have gone wrong and suggest solutions.
    If additional steps are needed to complete the user's original request, clearly outline them.
    """)
    
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "status": state["status"],
        "branches": state["branches"],
        "recent_commits": state["recent_commits"],
        "diff_stat": state["diff_stat"],
        "query": state["query"],
        "history": history_text
    })
    
    state["response"] = response
    return state

# Define routing logic
def router(state: GitAgentState) -> str:
    """Route to the next node based on the action type."""
    action_type = state["action"]["action_type"]
    
    if action_type == "execute_command":
        return "command_executor"
    elif action_type == "provide_info":
        return "info_provider"
    else:
        return END

def should_continue(state: GitAgentState) -> str:
    """Determine if we should continue or end."""
    # Check if execution was stopped due to errors
    if state.get("execution_stopped", False):
        return "responder"
    
    # Check if we need to re-analyze after command execution
    if state["action"]["action_type"] == "execute_command":
        # Look at the reasoning to see if more steps are needed
        reasoning = state["action"]["reasoning"]
        if "next step" in reasoning.lower() or "additional step" in reasoning.lower() or "subsequent step" in reasoning.lower():
            return "analyzer"
    
    return "responder"

# Build the graph
def build_git_agent() -> StateGraph:
    """Build the GitAgent workflow graph."""
    workflow = StateGraph(GitAgentState)
    
    # Add nodes
    workflow.add_node("analyzer", analyzer)
    workflow.add_node("command_executor", command_executor)
    workflow.add_node("info_provider", info_provider)
    workflow.add_node("responder", responder)
    workflow.add_node("router", router)  # Add router as a node
    workflow.add_node("should_continue", should_continue)  # Add should_continue as a node
    
    # Add edges with string names, not function references
    workflow.add_edge("analyzer", "router")
    workflow.add_edge("router", "command_executor")
    workflow.add_edge("router", "info_provider")
    workflow.add_edge("router", END)
    workflow.add_edge("command_executor", "should_continue")
    workflow.add_edge("should_continue", "analyzer")
    workflow.add_edge("should_continue", "responder")
    workflow.add_edge("info_provider", "responder")
    workflow.add_edge("responder", END)
    
    # Set the entry point
    workflow.set_entry_point("analyzer")
    
    return workflow

def main():
    parser = argparse.ArgumentParser(description="Git Agent - AI-powered Git assistant using LangGraph")
    parser.add_argument("query", nargs="*", help="Your query for the Git agent")
    parser.add_argument("--auto-approve", "-y", action="store_true", help="Automatically approve all recommended commands")
    args = parser.parse_args()
    
    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a Git repository. Please run this command from a Git repository root.")
        sys.exit(1)
    
    # Get the query from arguments or prompt the user
    if args.query:
        query = " ".join(args.query)
    else:
        query = input("What would you like to do with your Git repository? ")
    
    # Print a welcome message
    print("\n🔍 Analyzing your Git repository...")
    
    # Gather initial repository information
    initial_state = {
        "query": query,
        "status": get_git_status(),
        "branches": get_git_branch(),
        "recent_commits": get_git_log(),
        "diff_stat": get_git_diff(),
        "remote_branches": get_git_remote_branches(),
        "unpushed_commits": get_git_unpushed_commits(),
        "remotes": get_remotes(),
        "history": [],
        "action": {"action_type": "", "command": "", "reasoning": ""},
        "response": "",
        "execution_stopped": False
    }
    
    # Build and run the agent
    git_agent = build_git_agent().compile()
    
    # Configure command confirmation behavior
    if args.auto_approve:
        print("\n⚠️ Auto-approve mode enabled. All recommended Git commands will be executed without confirmation.")
    
    # Run the agent workflow
    final_state = git_agent.invoke(initial_state)
    
    # Display the final response
    print("\n✅ GitAgent Workflow Complete")
    print("----------------------------")
    print(final_state["response"])
    
    # If commands were executed, summarize them
    executed_commands = [entry["action"]["command"] for entry in final_state["history"] 
                        if "state" in entry and entry["state"] == "command_executor"]
    
    if executed_commands:
        print("\n📋 Summary of Executed Commands:")
        for i, cmd in enumerate(executed_commands, 1):
            print(f"{i}. git {cmd}")
    
    # Display next steps if there were errors
    if final_state.get("execution_stopped", False):
        print("\n⚠️ Workflow was interrupted due to errors or user request.")
        print("You may need to manually complete the remaining steps.")

if __name__ == "__main__":
    main() 