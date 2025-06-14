import json
from typing import Dict, List, Tuple, Any, Literal, TypedDict
from services.groq_api_service import GroqAPIService
from utils.input_handler import get_confirmation
from langgraph.graph import StateGraph, END

from utils.git_commands import (
    get_git_status, get_git_branch, get_git_remote_branches,
    get_git_log, get_git_diff, get_git_unpushed_commits,
    get_remotes, execute_git_command
)

# Define agent state and action models
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

class GitService:
    def __init__(self):
        self.groq_service = GroqAPIService()
        self.agent = self._build_agent()
    
    def get_repo_info(self) -> Dict[str, str]:
        """Gather comprehensive information about the current Git repository."""
        return {
            "status": get_git_status(),
            "branches": get_git_branch(),
            "remote_branches": get_git_remote_branches(),
            "recent_commits": get_git_log(),
            "diff_stat": get_git_diff(),
            "unpushed_commits": get_git_unpushed_commits(),
            "remotes": get_remotes()
        }
    
    # Agent workflow nodes
    def _analyzer(self, state: GitAgentState) -> GitAgentState:
        """Analyze the repository and decide what action to take."""
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations.
        Analyze the Git repository information provided and respond to the user's request.
        
        Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        User query: {state["query"]}
        
        IMPORTANT: You should be PROACTIVE and choose "execute_command" whenever the user wants to perform actual Git operations.
        
        Choose "execute_command" if the user wants to:
        - Add files (git add)
        - Commit changes (git commit)
        - Push changes (git push)
        - Pull changes (git pull)
        - Create or switch branches (git branch, git checkout, git switch)
        - Merge branches (git merge)
        - Rebase (git rebase)
        - Stash changes (git stash)
        - Reset changes (git reset)
        - Clone repositories (git clone)
        - Any other Git action that modifies the repository state
        
        Choose "provide_info" ONLY if the user is asking for:
        - Information about the current state
        - Help understanding Git concepts
        - Explanations of what happened
        - Questions about Git without wanting to perform actions
        
        For action-oriented queries like "add all changes", "commit this", "push to remote", etc., 
        you should ALWAYS choose "execute_command".
        
        CRITICAL: Return ONLY a valid JSON object, nothing else. No explanations, no additional text.
        
        JSON structure:
        {{
            "action_type": "execute_command" | "provide_info" | "end",
            "command": "the git command to execute (if applicable)",
            "reasoning": "your reasoning for this action, including any additional steps that will be needed"
        }}
        
        If you choose "execute_command":
        1. Put the FIRST command that needs to be run in the "command" field (without "git " prefix)
        2. In "reasoning", explain what this command will do and mention any subsequent steps needed
        
        Example for "add all changes":
        {{
            "action_type": "execute_command",
            "command": "add .",
            "reasoning": "This will stage all modified and new files for commit. After this, you'll likely want to commit these changes with a meaningful commit message."
        }}
        
        RESPOND WITH ONLY THE JSON OBJECT, NO OTHER TEXT.
        """
        
        response = self.groq_service.generate_response(prompt)
        
        if response is None:
            # Fallback action if API fails
            action = {
                "action_type": "end",
                "command": "",
                "reasoning": "API service unavailable. Please try again."
            }
        else:
            try:
                # Try to parse JSON response
                action = json.loads(response.strip())
            except json.JSONDecodeError as e:
                # Try to extract JSON from the response if it's mixed content
                try:
                    # Look for JSON in the response
                    import re
                    json_match = re.search(r'\{[^{}]*"action_type"[^{}]*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        action = json.loads(json_str)
                    else:
                        raise ValueError("No JSON found in response")
                except (json.JSONDecodeError, ValueError) as extract_error:
                    # If JSON parsing fails completely, try to detect intent from text
                    if any(keyword in response.lower() for keyword in ["add", "commit", "push", "pull", "merge", "checkout", "branch"]):
                        # Looks like a command request, try to extract it
                        if "add" in response.lower() and ("all" in response.lower() or "." in response):
                            action = {
                                "action_type": "execute_command",
                                "command": "add .",
                                "reasoning": "Extracted from response: stage all changes for commit"
                            }
                        else:
                            action = {
                                "action_type": "provide_info",
                                "command": "",
                                "reasoning": response
                            }
                    else:
                        action = {
                            "action_type": "provide_info",
                            "command": "",
                            "reasoning": response
                        }
        
        state["action"] = action
        # Add to history
        state["history"].append({"action": action, "state": "analyzer"})
        
        return state

    def _command_executor(self, state: GitAgentState) -> GitAgentState:
        """Execute the recommended Git command."""
        action = state["action"]
        
        if action["action_type"] != "execute_command" or not action["command"]:
            return state
        
        # Clean up the command
        command = action["command"]
        if command.startswith("git "):
            command = command[4:]
        
        # Ask for confirmation
        print(f"\n🔍 Recommended Git command: git {command}")
        print(f"📝 Reasoning: {action['reasoning']}")
        
        confirmed = get_confirmation(
            "\n❓ Do you want to execute this command?", 
            default_yes=True
        )
        
        if not confirmed:
            print("❌ Command execution cancelled by user.")
            state["execution_stopped"] = True
            state["response"] = f"Command execution cancelled: git {command}"
            return state
        
        # Execute the command
        print(f"\n🚀 Executing: git {command}")
        result = execute_git_command(command)
        
        # Update state with execution results
        state["response"] = f"✅ Command executed: git {command}\nResult:\n{result}"
        
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
            continue_execution = get_confirmation(
                "❓ Do you want to continue with the next steps?", 
                default_yes=False
            )
            
            if not continue_execution:
                print("❌ Workflow execution stopped by user.")
                state["execution_stopped"] = True
        
        return state

    def _info_provider(self, state: GitAgentState) -> GitAgentState:
        """Provide information without executing commands."""
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations.
        Based on the Git repository information, provide a helpful response to the user's query.
        
        Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        User query: {state["query"]}
        
        Your reasoning: {state["action"]["reasoning"]}
        
        Provide a clear and concise answer to the user's question. Include specific details from 
        the repository information provided above. If relevant, suggest Git commands that 
        the user could run, but format them clearly as suggestions, not as commands to be executed.
        """
        
        response = self.groq_service.generate_response(prompt)
        
        if response is None:
            response = "I'm sorry, I couldn't generate a response due to API issues. Please try again."
        
        state["response"] = response
        
        # Add to history
        state["history"].append({"response": response, "state": "info_provider"})
        
        return state

    def _responder(self, state: GitAgentState) -> GitAgentState:
        """Generate a final response based on the actions taken."""
        
        # Prepare history for context
        history_text = ""
        for entry in state["history"]:
            if "state" in entry:
                if entry["state"] == "command_executor" and "result" in entry:
                    history_text += f"Executed: git {entry['action']['command']}\nResult: {entry['result']}\n\n"
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations.
        Based on all information gathered and actions taken, provide a final response to the user's query.
        
        Current Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        User query: {state["query"]}
        
        Actions taken:
        {history_text}
        
        Provide a clear, helpful, and comprehensive final response to the user's query.
        Include explanations of what was done, what was found, and any additional recommendations.
        
        If the workflow was completed successfully, summarize the changes made.
        If there were any issues, explain what might have gone wrong and suggest solutions.
        If additional steps are needed to complete the user's original request, clearly outline them.
        """
        
        response = self.groq_service.generate_response(prompt)
        
        if response is None:
            response = "Workflow completed, but I couldn't generate a final summary due to API issues."
        
        state["response"] = response
        return state

    def _router(self, state: GitAgentState) -> str:
        """Route to the next node based on the action type."""
        action_type = state["action"]["action_type"]
        
        if action_type == "execute_command":
            return "command_executor"
        elif action_type == "provide_info":
            return "info_provider"
        else:
            return "end"

    def _should_continue(self, state: GitAgentState) -> str:
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

    def _build_agent(self) -> StateGraph:
        """Build the GitAgent workflow graph."""
        workflow = StateGraph(GitAgentState)
        
        # Add nodes (only the ones that modify state)
        workflow.add_node("analyzer", self._analyzer)
        workflow.add_node("command_executor", self._command_executor)
        workflow.add_node("info_provider", self._info_provider)
        workflow.add_node("responder", self._responder)
        
        # Add conditional edges (these use the routing functions)
        workflow.add_conditional_edges(
            "analyzer",
            self._router,
            {
                "command_executor": "command_executor",
                "info_provider": "info_provider",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "command_executor",
            self._should_continue,
            {
                "analyzer": "analyzer",
                "responder": "responder"
            }
        )
        
        # Simple edges
        workflow.add_edge("info_provider", "responder")
        workflow.add_edge("responder", END)
        
        # Set the entry point
        workflow.set_entry_point("analyzer")
        
        return workflow.compile()
    
    def process_query(self, query: str) -> Tuple[str, List[str]]:
        """Process a user query using the agentic workflow and return response and commands."""
        # Get repository information
        repo_info = self.get_repo_info()
        
        # Create initial state for the agent
        initial_state = {
            "query": query,
            "status": repo_info["status"],
            "branches": repo_info["branches"],
            "recent_commits": repo_info["recent_commits"],
            "diff_stat": repo_info["diff_stat"],
            "remote_branches": repo_info["remote_branches"],
            "unpushed_commits": repo_info["unpushed_commits"],
            "remotes": repo_info["remotes"],
            "history": [],
            "action": {"action_type": "", "command": "", "reasoning": ""},
            "response": "",
            "execution_stopped": False
        }
        
        # Run the agentic workflow
        print("\n🔍 Analyzing your Git repository...")
        final_state = self.agent.invoke(initial_state)
        
        # Extract commands from history for compatibility with controller
        executed_commands = []
        for entry in final_state["history"]:
            if "state" in entry and entry["state"] == "command_executor" and "action" in entry:
                executed_commands.append(entry["action"]["command"])
        
        # Return response and any commands that were suggested (for controller compatibility)
        return final_state["response"], executed_commands 