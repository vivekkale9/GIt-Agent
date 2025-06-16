import json
from typing import Dict, List, Tuple, Any, Literal, TypedDict
from services.groq_api_service import GroqAPIService
from utils.input_handler import get_confirmation
from utils.streaming import stream_text, stream_formatted_text
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
    workflow_step: int  # Track which step we're on in multi-step workflows
    original_branch: str  # Remember the original branch when workflow started
    workflow_context: Dict[str, Any]  # Track workflow-specific context

class GitService:
    def __init__(self):
        self.groq_service = GroqAPIService()
        self.agent = self._build_agent()
    
    def get_repo_info(self) -> Dict[str, str]:
        return {
            "status": get_git_status(),
            "branches": get_git_branch(),
            "remote_branches": get_git_remote_branches(),
            "recent_commits": get_git_log(),
            "diff_stat": get_git_diff(),
            "unpushed_commits": get_git_unpushed_commits(),
            "remotes": get_remotes()
        }
    
    def _extract_current_branch(self, branches_output: str) -> str:
        """Extract the current branch name from git branch output."""
        lines = branches_output.split('\n')
        for line in lines:
            if line.strip().startswith('*'):
                # Remove the * and any extra whitespace
                current_branch = line.strip()[1:].strip()
                # Handle detached HEAD state
                if current_branch.startswith('('):
                    return "HEAD (detached)"
                return current_branch
        return "unknown"
    
    # Agent workflow nodes
    def _analyzer(self, state: GitAgentState) -> GitAgentState:
        """Analyze the repository and decide what action to take."""
        
        # Check if this is a continuation of a multi-step workflow
        executed_commands = [entry["action"]["command"] for entry in state["history"] 
                           if "state" in entry and entry["state"] == "command_executor" and "action" in entry]
        
        context_info = ""
        if executed_commands:
            context_info = f"\nCommands already executed in this workflow: {', '.join([f'git {cmd}' for cmd in executed_commands])}"
        
        # Extract current branch from git status/branch info
        current_branch = self._extract_current_branch(state["branches"])
        
        # On first analysis, set up workflow context for branch operations
        if state["workflow_step"] == 0 and not state["workflow_context"]:
            original_query = state["query"].lower()
            
            # Parse the original intent and remember key context
            if "delete" in original_query and ("current branch" in original_query or "this branch" in original_query):
                state["workflow_context"]["target_branch_to_delete"] = state["original_branch"]
                state["workflow_context"]["delete_current_branch"] = True
                context_info += f"\nOriginal branch to delete: {state['original_branch']}"
            
            if "create" in original_query and "branch" in original_query:
                # Extract new branch name if possible
                import re
                branch_match = re.search(r'branch\s+(?:named\s+)?([^\s]+)', original_query)
                if branch_match:
                    state["workflow_context"]["new_branch_name"] = branch_match.group(1)
        
        # Use workflow context to avoid re-interpreting intent
        branch_to_delete = state["workflow_context"].get("target_branch_to_delete", current_branch)
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations with deep knowledge of Git constraints and best practices.
        
        Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Current branch: {current_branch}
        - Original branch (when workflow started): {state["original_branch"]}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        User query: {state["query"]}{context_info}
        
        WORKFLOW CONTEXT - IMPORTANT:
        - If user said "delete current branch" they meant the original branch: {state["original_branch"]}
        - Target branch to delete: {branch_to_delete}
        - Do NOT re-interpret "current branch" after switching branches
        - Workflow step: {state["workflow_step"]}
        
        IMPORTANT Git Workflow Rules - You MUST follow these:
        1. **Cannot delete current branch**: If user wants to delete the current branch, you MUST first checkout to a different branch (usually 'main' or 'master')
        2. **Branch deletion context**: When user says "delete current branch", they mean the branch they were on when they started ({state["original_branch"]}), NOT the branch they're on now after switching
        3. **Branch creation flow**: When creating branches, ensure you're on the right base branch first
        4. **Staging before commit**: Always stage changes before committing
        5. **Push new branches**: Use -u flag when pushing new branches for the first time
        
        PROACTIVE ERROR PREVENTION:
        - If user wants to delete original branch "{state["original_branch"]}" and we're still on it, first command should be switching to 'main' or 'master'
        - Once we've switched away from "{state["original_branch"]}", we can safely delete it
        - If user wants to commit but files aren't staged, add staging step first
        - If user wants to push a new branch, include the -u origin flag
        
        Multi-step workflow handling:
        1. Execute ONE command at a time
        2. After each command, user will be asked for confirmation for the NEXT step
        3. Continue until the entire user request is fulfilled
        4. Account for Git constraints in your command sequence
        5. Remember original context - don't re-interpret after branch switches
        
        Choose "execute_command" for Git operations:
        - Add files (git add)
        - Commit changes (git commit)
        - Push changes (git push)
        - Pull changes (git pull)
        - Create or switch branches (git branch, git checkout, git switch)
        - Merge branches (git merge) 
        - Delete branches (git branch -d/-D) - BUT checkout first if deleting current branch
        - Stash changes (git stash)
        - Reset changes (git reset)
        
        Choose "provide_info" ONLY for:
        - Information requests
        - Help with Git concepts
        - Status explanations
        - Non-action queries
        
        For multi-step queries, determine the NEXT command based on:
        1. User's original request (interpreted once at the beginning)
        2. Commands already executed
        3. Git workflow constraints and best practices
        4. What still needs to be done
        5. Workflow context (don't re-interpret original intent)
        
        CRITICAL: Return ONLY a valid JSON object, nothing else.
        
        JSON structure:
        {{
            "action_type": "execute_command" | "provide_info" | "end",
            "command": "the git command to execute (if applicable)",
            "reasoning": "your reasoning for this action, including any additional steps that will be needed"
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
        
        # Ask for confirmation with streaming display
        step_info = f" (Step {state['workflow_step'] + 1})" if state['workflow_step'] > 0 else ""
        print("\n", end='')
        stream_text(f"🔍 Recommended Git command{step_info}: ", delay=0.025, end='')
        stream_text(f"git {command}", delay=0.015, end='\n')
        
        print("")  # Empty line for spacing
        stream_text("📝 Reasoning: ", delay=0.025, end='')
        stream_formatted_text(action['reasoning'], delay=0.015)
        
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
        state["workflow_step"] += 1  # Increment step counter
        
        # Update workflow context to track completed operations
        if "branch -d" in command or "branch -D" in command:
            state["workflow_context"]["branch_deleted"] = True
        elif "checkout -b" in command or "switch -c" in command:
            state["workflow_context"]["new_branch_created"] = True
        elif command.startswith("add"):
            state["workflow_context"]["changes_staged"] = True
        elif command.startswith("commit"):
            state["workflow_context"]["changes_committed"] = True
        elif command.startswith("push"):
            state["workflow_context"]["changes_pushed"] = True
        
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
            print("\n", end='')
            stream_text("⚠️ There might be an issue with the command execution.", delay=0.025)
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
            reasoning = state["action"]["reasoning"]
            original_query = state["query"].lower()
            
            executed_commands = [entry["action"]["command"] for entry in state["history"] 
                               if "state" in entry and entry["state"] == "command_executor" and "action" in entry]
            
            # Check for explicit continuation indicators in reasoning
            continuation_keywords = [
                "next step", "additional step", "subsequent step", "then", "after this",
                "following", "next", "continue", "more steps", "still need", "will be to"
            ]
            
            has_continuation_indicator = any(keyword in reasoning.lower() for keyword in continuation_keywords)
            
            # Enhanced workflow pattern detection using context
            unfulfilled_operations = []
            
            # Use workflow context to track what still needs to be done
            workflow_context = state.get("workflow_context", {})
            
            # Pattern: Delete original branch workflow
            if workflow_context.get("delete_current_branch"):
                target_branch = workflow_context.get("target_branch_to_delete")
                if target_branch:
                    # Check if we've already deleted the target branch using context flag
                    branch_already_deleted = workflow_context.get("branch_deleted", False)
                    
                    if not branch_already_deleted:
                        # Check if we've switched away from the target branch first
                        if any("checkout" in cmd or "switch" in cmd for cmd in executed_commands):
                            unfulfilled_operations.append("delete original branch")
                        else:
                            unfulfilled_operations.append("checkout to safe branch first")
            
            # Pattern: Create new branch  
            if "create" in original_query and "branch" in original_query:
                new_branch_created = workflow_context.get("new_branch_created", False)
                if not new_branch_created:
                    unfulfilled_operations.append("create new branch")
            
            # Pattern: Add/stage changes
            if any(keyword in original_query for keyword in ["add", "stage", "changes"]):
                changes_staged = workflow_context.get("changes_staged", False)
                if not changes_staged:
                    unfulfilled_operations.append("stage changes")
            
            # Pattern: Commit changes
            if "commit" in original_query:
                changes_committed = workflow_context.get("changes_committed", False)
                if not changes_committed:
                    unfulfilled_operations.append("commit changes")
            
            # Pattern: Push changes
            if "push" in original_query:
                changes_pushed = workflow_context.get("changes_pushed", False)
                if not changes_pushed:
                    unfulfilled_operations.append("push changes")
            
            # Count distinct operations mentioned vs executed
            operation_keywords = ["delete", "create", "add", "stage", "commit", "push", "merge", "checkout", "switch"]
            mentioned_operations = sum(1 for keyword in operation_keywords if keyword in original_query)
            
            # Continue if there are clear signs more steps are needed
            should_continue = (
                has_continuation_indicator or  # Reasoning explicitly mentions more steps
                unfulfilled_operations or  # Specific operations still pending
                (mentioned_operations > len(executed_commands))  # More operations mentioned than executed
            )
            
            if should_continue:
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
        repo_info = self.get_repo_info()
        
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
            "execution_stopped": False,
            "workflow_step": 0,
            "original_branch": self._extract_current_branch(repo_info["branches"]),
            "workflow_context": {}
        }
        
        # Run the agentic workflow
        print("\n", end='')
        stream_text("🔍 Analyzing your Git repository...", delay=0.03)
        final_state = self.agent.invoke(initial_state)
        
        # Extract commands from history for compatibility with controller
        executed_commands = []
        for entry in final_state["history"]:
            if "state" in entry and entry["state"] == "command_executor" and "action" in entry:
                executed_commands.append(entry["action"]["command"])
        
        # Return response and any commands that were suggested (for controller compatibility)
        return final_state["response"], executed_commands 