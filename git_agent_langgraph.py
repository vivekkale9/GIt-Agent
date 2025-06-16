#!/usr/bin/env python3

import json
import os
import sys
import argparse
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any, Literal, TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, END
from services.groq_api_service import GroqAPIService
from utils.input_handler import get_confirmation
from utils.streaming import stream_text, stream_formatted_text
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
    expected_outcome: str
    verification_commands: List[str]

class WorkflowSession(TypedDict):
    session_id: str
    created_at: str
    original_query: str
    original_branch: str
    workflow_context: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    current_step: int
    status: Literal["active", "completed", "failed", "paused"]

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
    workflow_step: int
    original_branch: str
    workflow_context: Dict[str, Any]
    session: WorkflowSession
    auto_approve: bool
    verification_results: Dict[str, Any]

class UnifiedGitAgent:
    def __init__(self, auto_approve: bool = False):
        self.groq_service = GroqAPIService()
        self.auto_approve = auto_approve
        self.agent = self._build_agent()
        self.session_dir = Path(".git") / "gitagent_sessions"
        self.session_dir.mkdir(exist_ok=True)
        
    def _get_session_file(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"
    
    def _save_session(self, session: WorkflowSession):
        """Persist session state to disk."""
        session_file = self._get_session_file(session["session_id"])
        with open(session_file, 'w') as f:
            json.dump(session, f, indent=2)
    
    def _load_session(self, session_id: str) -> WorkflowSession:
        """Load session state from disk."""
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return None
    
    def _find_active_session(self) -> WorkflowSession:
        """Find an active session for the current repository."""
        if not self.session_dir.exists():
            return None
            
        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    if session.get("status") == "active":
                        return session
            except (json.JSONDecodeError, IOError):
                continue
        return None
    
    def _create_session(self, query: str, original_branch: str) -> WorkflowSession:
        """Create a new workflow session."""
        session_id = f"session_{int(time.time())}"
        session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "original_query": query,
            "original_branch": original_branch,
            "workflow_context": {},
            "execution_history": [],
            "current_step": 0,
            "status": "active"
        }
        self._save_session(session)
        return session
    
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
                current_branch = line.strip()[1:].strip()
                if current_branch.startswith('('):
                    return "HEAD (detached)"
                return current_branch
        return "unknown"
    
    def _verify_command_success(self, command: str, expected_outcome: str, verification_commands: List[str]) -> Dict[str, Any]:
        """Verify if a command achieved its expected outcome."""
        verification_results = {
            "success": True,
            "details": {},
            "issues": []
        }
        
        # Run verification commands
        for verify_cmd in verification_commands:
            try:
                result = execute_git_command(verify_cmd)
                verification_results["details"][verify_cmd] = result
                
                # Check for common failure indicators
                if "error" in result.lower() or "fatal" in result.lower():
                    verification_results["success"] = False
                    verification_results["issues"].append(f"Verification command '{verify_cmd}' returned error: {result}")
                    
            except Exception as e:
                verification_results["success"] = False
                verification_results["issues"].append(f"Failed to run verification command '{verify_cmd}': {str(e)}")
        
        # Enhanced semantic verification based on command type
        if "branch -d" in command or "branch -D" in command:
            # Verify branch was actually deleted
            current_branches = get_git_branch()
            deleted_branch = command.split()[-1]
            if deleted_branch in current_branches:
                verification_results["success"] = False
                verification_results["issues"].append(f"Branch {deleted_branch} still exists after deletion attempt")
        
        elif "checkout" in command or "switch" in command:
            # Verify we're on the expected branch
            current_branch = self._extract_current_branch(get_git_branch())
            expected_branch = command.split()[-1]
            if current_branch != expected_branch:
                verification_results["success"] = False
                verification_results["issues"].append(f"Expected to be on branch {expected_branch}, but on {current_branch}")
        
        elif "add" in command:
            # Verify files were staged
            status_output = get_git_status()
            if "Changes to be committed:" not in status_output and "nothing to commit" not in status_output:
                verification_results["success"] = False
                verification_results["issues"].append("Files were not properly staged")
        
        elif "commit" in command:
            # Verify commit was successful - check that there are no longer staged changes
            status_output = get_git_status()
            if "Changes to be committed:" in status_output:
                verification_results["success"] = False
                verification_results["issues"].append("Commit failed - changes are still staged")
            elif "nothing to commit, working tree clean" in status_output or "Your branch is ahead of" in status_output:
                # This indicates a successful commit
                pass
            else:
                # Check if we have any indication of successful commit
                log_result = verification_results["details"].get("log -1", "")
                if not log_result or "commit" not in log_result:
                    verification_results["success"] = False
                    verification_results["issues"].append("Unable to verify commit was created")
        
        elif "push" in command:
            # Verify push was successful
            status_output = get_git_status()
            if "Your branch is ahead of" in status_output:
                verification_results["success"] = False
                verification_results["issues"].append("Push failed - branch is still ahead of remote")
            elif "up to date" in status_output.lower() or "up-to-date" in status_output.lower():
                # This indicates successful push
                pass
        
        return verification_results

    def _analyzer(self, state: GitAgentState) -> GitAgentState:
        """Analyze the repository and decide what action to take."""
        
        # Load context from session
        session = state["session"]
        executed_commands = [entry["command"] for entry in session["execution_history"]]
        
        context_info = ""
        if executed_commands:
            context_info = f"\nCommands already executed in this session: {', '.join([f'git {cmd}' for cmd in executed_commands])}"
            
            # Add verification results from previous commands
            failed_commands = [entry for entry in session["execution_history"] if not entry.get("verification_success", True)]
            if failed_commands:
                context_info += f"\nPrevious command failures: {[entry['command'] for entry in failed_commands]}"
        
        current_branch = self._extract_current_branch(state["branches"])
        
        # Enhanced workflow context parsing
        if state["workflow_step"] == 0 and not state["workflow_context"]:
            original_query = session["original_query"].lower()
            
            
            if "delete" in original_query and ("current branch" in original_query or "this branch" in original_query):
                state["workflow_context"]["target_branch_to_delete"] = session["original_branch"]
                state["workflow_context"]["delete_current_branch"] = True
                context_info += f"\nOriginal branch to delete: {session['original_branch']}"
            
            if "create" in original_query and "branch" in original_query:
                import re
                branch_match = re.search(r'branch\s+(?:named\s+)?(?:with name\s+)?([^\s]+)', original_query)
                if branch_match:
                    state["workflow_context"]["new_branch_name"] = branch_match.group(1)
            
            # Store workflow context in session
            session["workflow_context"] = state["workflow_context"]
            self._save_session(session)
        
        branch_to_delete = state["workflow_context"].get("target_branch_to_delete", current_branch)
        
        # Determine if this is clearly an action request vs information request
        action_keywords = ["unstage", "stage", "commit", "push", "create", "delete", "checkout", "switch", "merge", "rebase", "add", "remove"]
        original_query_lower = session["original_query"].lower()
        is_action_request = any(keyword in original_query_lower for keyword in action_keywords)
        
        # Check if this is first step and we have actionable request
        if state["workflow_step"] == 0 and is_action_request:
            force_action = True
        else:
            force_action = False
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations. You MUST execute Git commands when the user requests actions.
        
        PERSISTENT SESSION CONTEXT:
        - Session ID: {session["session_id"]}
        - Original Query: {session["original_query"]}
        - Original Branch: {session["original_branch"]}
        - Current Step: {state["workflow_step"] + 1}
        
        Current Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Current branch: {current_branch}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        EXECUTION HISTORY:{context_info}
        
        WORKFLOW CONTEXT:
        - Target branch to delete: {branch_to_delete}
        - Workflow context: {state["workflow_context"]}
        
        CRITICAL INSTRUCTIONS:
        1. The user wants ACTIONS to be executed, not just information
        2. For multi-step requests, execute ONE command at a time
        3. ALWAYS choose "execute_command" for action requests like: unstage, stage, commit, push, create branch, etc.
        4. ONLY choose "provide_info" for pure information questions like "what is the status?"
        5. Include specific verification commands to confirm each step worked
        
        INTERACTIVE COMMAND HANDLING:
        - For rebase operations, use non-interactive flags to prevent hanging
        - For merge operations, include --no-edit to avoid editor
        - For commits without messages, provide default message
        - NEVER use commands that require user interaction in automated mode
        
        Git Workflow Rules:
        1. Cannot delete current branch - checkout to different branch first
        2. When user says "delete current branch" they mean original branch: {session["original_branch"]}
        3. Verify prerequisites before executing
        4. If previous commands failed, address those issues first
        5. For rebase, use: "rebase <target-branch>" (system will add non-interactive flags)
        6. For interactive operations, warn about complexity and provide safer alternatives
        
        For the query "{session["original_query"]}", determine the NEXT SPECIFIC COMMAND to execute.
        
        Examples of good responses:
        - For "unstage changes": {{"action_type": "execute_command", "command": "reset HEAD .", "reasoning": "...", "expected_outcome": "...", "verification_commands": ["status"]}}
        - For "rebase onto main": {{"action_type": "execute_command", "command": "rebase main", "reasoning": "...", "expected_outcome": "...", "verification_commands": ["status", "log --oneline -5"]}}
        
        RESPOND WITH ONLY A VALID JSON OBJECT:
        {{
            "action_type": "execute_command",
            "command": "specific git command without git prefix",
            "reasoning": "why this specific command is needed now",
            "expected_outcome": "what should happen after execution",
            "verification_commands": ["commands", "to", "verify", "success"]
        }}
        """
        
        # Add debugging to see what the AI is returning
        print(f"\n🤖 Sending query to AI for step {state['workflow_step'] + 1}...")
        response = self.groq_service.generate_response(prompt)
        print(f"🤖 AI Raw Response: {response}")
        
        if response is None:
            action = {
                "action_type": "end",
                "command": "",
                "reasoning": "API service unavailable. Please try again.",
                "expected_outcome": "",
                "verification_commands": []
            }
        else:
            try:
                # Clean up the response - remove any non-JSON content
                response_clean = response.strip()
                
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', response_clean, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    action = json.loads(json_str)
                    
                    # Ensure required fields exist
                    if "action_type" not in action:
                        action["action_type"] = "execute_command" if force_action else "provide_info"
                    if "command" not in action:
                        action["command"] = ""
                    if "reasoning" not in action:
                        action["reasoning"] = "Generated from response"
                    if "expected_outcome" not in action:
                        action["expected_outcome"] = ""
                    if "verification_commands" not in action:
                        action["verification_commands"] = ["status"]
                        
                else:
                    raise ValueError("No JSON found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"⚠️ Raw response: {response}")
                
                # For action requests, force execute_command with fallback logic
                if force_action or is_action_request:
                    original_query = session["original_query"].lower()
                    
                    # Simple fallback logic for common operations
                    if state["workflow_step"] == 0:
                        if "unstage" in original_query:
                            action = {
                                "action_type": "execute_command",
                                "command": "reset HEAD .",
                                "reasoning": "Unstaging all staged changes as requested",
                                "expected_outcome": "All staged changes will be unstaged",
                                "verification_commands": ["status"]
                            }
                        elif "create" in original_query and "branch" in original_query:
                            import re
                            branch_match = re.search(r'(?:branch\s+(?:named\s+)?(?:with name\s+)?)([^\s]+)', original_query)
                            branch_name = branch_match.group(1) if branch_match else "new-branch"
                            action = {
                                "action_type": "execute_command",
                                "command": f"checkout -b {branch_name}",
                                "reasoning": f"Creating new branch {branch_name} as requested",
                                "expected_outcome": f"New branch {branch_name} will be created and checked out",
                                "verification_commands": ["branch"]
                            }
                        else:
                            action = {
                                "action_type": "execute_command",
                                "command": "status",
                                "reasoning": "Checking repository status to determine next action",
                                "expected_outcome": "Repository status will be displayed",
                                "verification_commands": []
                            }
                    else:
                        # For subsequent steps, provide info as fallback
                        action = {
                            "action_type": "provide_info",
                            "command": "",
                            "reasoning": response,
                            "expected_outcome": "",
                            "verification_commands": []
                        }
                else:
                    action = {
                        "action_type": "provide_info",
                        "command": "",
                        "reasoning": response,
                        "expected_outcome": "",
                        "verification_commands": []
                    }
        
        print(f"🎯 Final Action: {action['action_type']} - {action.get('command', 'N/A')}")
        
        state["action"] = action
        state["history"].append({"action": action, "state": "analyzer", "timestamp": datetime.now().isoformat()})
        
        return state

    def _command_executor(self, state: GitAgentState) -> GitAgentState:
        """Execute the recommended Git command with verification."""
        action = state["action"]
        session = state["session"]
        
        if action["action_type"] != "execute_command" or not action["command"]:
            return state
        
        command = action["command"]
        if command.startswith("git "):
            command = command[4:]
        
        # Display command information
        step_info = f" (Step {state['workflow_step'] + 1})"
        print("\n", end='')
        stream_text(f"🔍 Recommended Git command{step_info}: ", delay=0.025, end='')
        stream_text(f"git {command}", delay=0.015, end='\n')
        
        print("")
        stream_text("📝 Reasoning: ", delay=0.025, end='')
        stream_formatted_text(action['reasoning'], delay=0.015)
        
        if action.get("expected_outcome"):
            print("")
            stream_text("🎯 Expected outcome: ", delay=0.025, end='')
            stream_formatted_text(action['expected_outcome'], delay=0.015)
        
        # Get confirmation unless auto-approve is enabled
        if not self.auto_approve:
            confirmed = get_confirmation(
                "\n❓ Do you want to execute this command?", 
                default_yes=True
            )
            
            if not confirmed:
                print("❌ Command execution cancelled by user.")
                state["execution_stopped"] = True
                state["response"] = f"Command execution cancelled: git {command}"
                session["status"] = "paused"
                self._save_session(session)
                return state
        
        # Execute the command
        print(f"\n🚀 Executing: git {command}")
        result = execute_git_command(command)
        
        # Verify command success
        verification_results = self._verify_command_success(
            command, 
            action.get("expected_outcome", ""), 
            action.get("verification_commands", [])
        )
        
        # Update execution history in session
        execution_entry = {
            "step": state["workflow_step"] + 1,
            "command": command,
            "reasoning": action["reasoning"],
            "expected_outcome": action.get("expected_outcome", ""),
            "result": result,
            "verification_success": verification_results["success"],
            "verification_details": verification_results,
            "timestamp": datetime.now().isoformat()
        }
        
        session["execution_history"].append(execution_entry)
        session["current_step"] = state["workflow_step"] + 1
        
        # Display results
        if verification_results["success"]:
            print("✅ Command executed successfully!")
            if verification_results["details"]:
                print("🔍 Verification passed:")
                for cmd, output in verification_results["details"].items():
                    if output.strip():
                        print(f"  • {cmd}: {output[:100]}...")
        else:
            print("⚠️ Command execution had issues:")
            for issue in verification_results["issues"]:
                print(f"  • {issue}")
            
            # Ask user how to proceed with failures
            if not self.auto_approve:
                continue_execution = get_confirmation(
                    "❓ Do you want to continue with the workflow despite these issues?", 
                    default_yes=False
                )
                
                if not continue_execution:
                    print("❌ Workflow execution stopped by user.")
                    state["execution_stopped"] = True
                    session["status"] = "failed"
                    self._save_session(session)
                    return state
        
        # Update state
        state["response"] = f"Command executed: git {command}\nResult: {result}"
        state["workflow_step"] += 1
        state["verification_results"] = verification_results
        
        # Update workflow context based on successful operations
        if verification_results["success"]:
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
        
        # Save updated session state
        session["workflow_context"] = state["workflow_context"]
        self._save_session(session)
        
        # Refresh repository info after command execution
        repo_info = self.get_repo_info()
        state.update(repo_info)
        
        return state

    def _info_provider(self, state: GitAgentState) -> GitAgentState:
        """Provide information without executing commands."""
        
        session = state["session"]
        execution_history = "\n".join([
            f"Step {entry['step']}: git {entry['command']} - {'✅' if entry['verification_success'] else '❌'}"
            for entry in session["execution_history"]
        ])
        
        prompt = f"""
        You are GitAgent, an AI assistant specialized in Git operations.
        
        SESSION CONTEXT:
        - Original Query: {session["original_query"]}
        - Execution History: {execution_history}
        
        Current Git repository information:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Recent commits: {state["recent_commits"]}
        - Current changes: {state["diff_stat"]}
        
        User query: {state["query"]}
        Reasoning: {state["action"]["reasoning"]}
        
        Provide a clear and comprehensive answer considering the full session context.
        Include specific details from the repository information and execution history.
        If relevant, suggest Git commands but format them clearly as suggestions.
        """
        
        response = self.groq_service.generate_response(prompt)
        
        if response is None:
            response = "I'm sorry, I couldn't generate a response due to API issues. Please try again."
        
        state["response"] = response
        state["history"].append({"response": response, "state": "info_provider", "timestamp": datetime.now().isoformat()})
        
        return state

    def _responder(self, state: GitAgentState) -> GitAgentState:
        """Generate a final response based on the actions taken."""
        
        session = state["session"]
        
        # Prepare execution summary
        if session["execution_history"]:
            history_text = "Execution Summary:\n"
            for entry in session["execution_history"]:
                status_icon = "✅" if entry["verification_success"] else "❌"
                history_text += f"{status_icon} Step {entry['step']}: git {entry['command']}\n"
                if not entry["verification_success"]:
                    history_text += f"   Issues: {', '.join(entry['verification_details']['issues'])}\n"
        else:
            history_text = "No commands were executed in this session."
        
        prompt = f"""
        You are GitAgent, providing a final comprehensive response.
        
        SESSION SUMMARY:
        - Original Query: {session["original_query"]}
        - Session Duration: {session["current_step"]} steps
        - Session Status: {session["status"]}
        
        {history_text}
        
        Current repository state:
        - Status: {state["status"]}
        - Current branches: {state["branches"]}
        - Recent commits: {state["recent_commits"]}
        
        Provide a comprehensive final response that:
        1. Summarizes what was accomplished
        2. Explains the current state of the repository
        3. Identifies any remaining issues or next steps
        4. Gives recommendations for future actions if needed
        
        Be specific about the success or failure of each operation.
        """
        
        response = self.groq_service.generate_response(prompt)
        
        if response is None:
            response = f"Workflow completed. {history_text}"
        
        state["response"] = response
        
        # Mark session as completed if no issues
        if not state.get("execution_stopped", False):
            session["status"] = "completed"
            self._save_session(session)
        
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
        """Determine if we should continue or end the workflow."""
        
        # Check if execution was stopped
        if state.get("execution_stopped", False):
            print("🛑 Execution was stopped by user")
            return "responder"
        
        # Check if we need to continue based on workflow analysis
        if state["action"]["action_type"] == "execute_command":
            session = state["session"]
            original_query = session["original_query"].lower()
            workflow_context = state["workflow_context"]
            executed_commands = [entry["command"] for entry in session["execution_history"]]
            
            print(f"\n🔍 Workflow Analysis:")
            print(f"   Original query: '{session['original_query']}'")
            print(f"   Commands executed: {executed_commands}")
            print(f"   Current step: {state['workflow_step']}")
            
            # Count total operations mentioned in the original query
            operation_keywords = [
                "switch", "checkout", "pull", "push", "merge", "rebase", 
                "create", "delete", "add", "stage", "commit", "unstage",
                "stash", "reset", "cherry-pick", "tag", "fetch"
            ]
            
            # Count how many distinct operations were mentioned
            mentioned_operations = []
            for keyword in operation_keywords:
                if keyword in original_query:
                    mentioned_operations.append(keyword)
            
            print(f"   Operations mentioned: {mentioned_operations}")
            
            # Special handling for compound operations
            operations_needed = 0
            workflow_incomplete = False
            
            # Analyze the specific query patterns
            if ("switch" in original_query or "checkout" in original_query) and "pull" in original_query and "merge" in original_query:
                # Pattern: "Switch to main, pull latest changes, and merge into current branch"
                print("   📋 Detected: Switch + Pull + Merge workflow")
                
                has_switched = any("checkout" in cmd or "switch" in cmd for cmd in executed_commands)
                has_pulled = any("pull" in cmd for cmd in executed_commands)
                has_merged = any("merge" in cmd for cmd in executed_commands)
                
                print(f"   ✅ Switched: {has_switched}, Pulled: {has_pulled}, Merged: {has_merged}")
                
                if not has_switched:
                    workflow_incomplete = True
                    print("   ⏳ Still need to switch branch")
                elif not has_pulled:
                    workflow_incomplete = True  
                    print("   ⏳ Still need to pull changes")
                elif not has_merged:
                    workflow_incomplete = True
                    print("   ⏳ Still need to merge changes")
                
                operations_needed = 3
                
            elif "pull" in original_query and "merge" in original_query:
                # Pattern: pull + merge
                print("   📋 Detected: Pull + Merge workflow")
                
                has_pulled = any("pull" in cmd for cmd in executed_commands)
                has_merged = any("merge" in cmd for cmd in executed_commands)
                
                print(f"   ✅ Pulled: {has_pulled}, Merged: {has_merged}")
                
                if not has_pulled or not has_merged:
                    workflow_incomplete = True
                    
                operations_needed = 2
                
            elif ("stage" in original_query or "add" in original_query) and "commit" in original_query:
                # Pattern: stage + commit + optional push
                print("   📋 Detected: Stage + Commit workflow")
                
                has_staged = any("add" in cmd for cmd in executed_commands)
                has_committed = any("commit" in cmd for cmd in executed_commands)
                has_pushed = any("push" in cmd for cmd in executed_commands)
                
                print(f"   ✅ Staged: {has_staged}, Committed: {has_committed}, Pushed: {has_pushed}")
                
                operations_needed = 2
                if "push" in original_query:
                    operations_needed = 3
                
                if not has_staged or not has_committed:
                    workflow_incomplete = True
                elif "push" in original_query and not has_pushed:
                    workflow_incomplete = True
                    
            elif "create" in original_query and "branch" in original_query:
                # Pattern: create branch
                print("   📋 Detected: Create Branch workflow")
                
                has_created_branch = any("checkout -b" in cmd or "switch -c" in cmd for cmd in executed_commands)
                
                print(f"   ✅ Created branch: {has_created_branch}")
                
                operations_needed = 1
                if not has_created_branch and not workflow_context.get("new_branch_created"):
                    workflow_incomplete = True
                    
            elif workflow_context.get("delete_current_branch"):
                # Pattern: delete branch workflow
                print("   📋 Detected: Delete Branch workflow")
                
                if not workflow_context.get("branch_deleted"):
                    workflow_incomplete = True
                    operations_needed = 2  # switch + delete
                    
            else:
                # General pattern: count operations
                print("   📋 General workflow - counting operations")
                operations_needed = len(mentioned_operations)
                
                if len(executed_commands) < operations_needed:
                    workflow_incomplete = True
            
            # Check if the last command failed verification
            last_verification = state.get("verification_results", {})
            command_failed = not last_verification.get("success", True)
            
            print(f"   📊 Summary:")
            print(f"      Operations needed: {operations_needed}")
            print(f"      Commands executed: {len(executed_commands)}")
            print(f"      Workflow incomplete: {workflow_incomplete}")
            print(f"      Last command failed: {command_failed}")
            
            # Continue if workflow is incomplete or last command failed
            if workflow_incomplete or command_failed:
                print(f"🔄 CONTINUING workflow")
                return "analyzer"
            else:
                print(f"✅ COMPLETING workflow")
        else:
            print("ℹ️ Not an execute_command action, ending workflow")
        
        return "responder"

    def _build_agent(self) -> StateGraph:
        """Build the unified GitAgent workflow graph."""
        workflow = StateGraph(GitAgentState)
        
        # Add nodes
        workflow.add_node("analyzer", self._analyzer)
        workflow.add_node("command_executor", self._command_executor)
        workflow.add_node("info_provider", self._info_provider)
        workflow.add_node("responder", self._responder)
        
        # Add conditional edges
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
        
        # Set entry point
        workflow.set_entry_point("analyzer")
        
        return workflow.compile()
    
    def process_query(self, query: str) -> Tuple[str, List[str]]:
        """Process a query with full session management and context persistence."""
        
        # Check for active session
        active_session = self._find_active_session()
        
        if active_session:
            print(f"📂 Resuming active session: {active_session['session_id']}")
            print(f"   Original query: {active_session['original_query']}")
            print(f"   Steps completed: {active_session['current_step']}")
            
            # Ask if user wants to continue or start fresh
            if not self.auto_approve:
                continue_session = get_confirmation(
                    "❓ Do you want to continue the existing workflow?",
                    default_yes=True
                )
                
                if not continue_session:
                    active_session["status"] = "completed"
                    self._save_session(active_session)
                    active_session = None
        
        # Get current repository info
        repo_info = self.get_repo_info()
        current_branch = self._extract_current_branch(repo_info["branches"])
        
        # Create or use existing session
        if active_session:
            session = active_session
            # Update query to continue workflow
            if query.lower() not in ["continue", "resume"]:
                query = f"Continue previous workflow: {active_session['original_query']}. Additional request: {query}"
        else:
            session = self._create_session(query, current_branch)
        
        # Initialize state
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
            "action": {"action_type": "", "command": "", "reasoning": "", "expected_outcome": "", "verification_commands": []},
            "response": "",
            "execution_stopped": False,
            "workflow_step": session["current_step"],
            "original_branch": session["original_branch"],
            "workflow_context": session.get("workflow_context", {}),
            "session": session,
            "auto_approve": self.auto_approve,
            "verification_results": {}
        }
        
        # Run the agent workflow
        print("\n", end='')
        stream_text("🔍 Analyzing your Git repository and workflow context...", delay=0.03)
        final_state = self.agent.invoke(initial_state)
        
        # Extract executed commands for compatibility
        executed_commands = [entry["command"] for entry in session["execution_history"]]
        
        return final_state["response"], executed_commands

def main():
    parser = argparse.ArgumentParser(description="Unified GitAgent - AI-powered Git assistant with persistent context")
    parser.add_argument("query", nargs="*", help="Your query for the Git agent")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve all commands")
    
    args = parser.parse_args()
    
    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a Git repository. Please run this command from a Git repository root.")
        sys.exit(1)
    
    if args.query:
        query = " ".join(args.query)
    else:
        query = input("What would you like to do with your Git repository? ")
    
    agent = UnifiedGitAgent(auto_approve=args.auto_approve)
    response, executed_commands = agent.process_query(query)
    
    print("\n" + "="*60)
    print("🎯 GitAgent Response:")
    print("="*60)
    print(response)
    
    if executed_commands:
        print(f"\n📋 Commands executed in this session: {len(executed_commands)}")
        for i, cmd in enumerate(executed_commands, 1):
            print(f"  {i}. git {cmd}")

if __name__ == "__main__":
    main() 