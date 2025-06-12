from typing import Dict, List, Tuple
from langchain_community.llms.ollama import Ollama
from langchain_core.output_parsers import StrOutputParser

from utils.git_commands import (
    get_git_status, get_git_branch, get_git_remote_branches,
    get_git_log, get_git_diff, get_git_unpushed_commits,
    get_remotes, execute_git_command
)
from utils.prompt_templates import git_agent_prompt_template

class GitService:
    def __init__(self):
        self.llm = Ollama(model="llama2")
        self.output_parser = StrOutputParser()
    
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
    
    def extract_commands(self, response: str) -> List[str]:
        """Extract Git commands from the response."""
        commands = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith("COMMAND: git "):
                # Extract the command, keeping the 'git' prefix
                cmd = line[len("COMMAND: "):]
                commands.append(cmd)
        return commands
    
    def execute_commands(self, commands: List[str]) -> List[Tuple[str, str]]:
        """Execute a list of Git commands and return results."""
        results = []
        for i, cmd in enumerate(commands, 1):
            print(f"\nExecuting step {i}: {cmd}")
            
            # Remove 'git ' prefix for execution
            if cmd.startswith("git "):
                cmd = cmd[4:]
            
            # Execute the command
            result = execute_git_command(cmd)
            print(f"Result: {result}")
            results.append((cmd, result))
            
            # Check for errors and ask to continue
            if "error" in result.lower() or "conflict" in result.lower():
                print("\n⚠️ Error detected in command execution.")
                continue_execution = input("Do you want to continue with the next steps? (yes/no): ").lower()
                if continue_execution not in ["yes", "y"]:
                    print("Workflow execution stopped.")
                    break
                
        return results
    
    def process_query(self, query: str) -> Tuple[str, List[str]]:
        """Process a user query and return AI response and suggested commands."""
        # Get repository information
        repo_info = self.get_repo_info()
        repo_info["user_query"] = query
        
        # Get AI response
        chain = git_agent_prompt_template | self.llm | self.output_parser
        response = chain.invoke(repo_info)
        
        # Extract commands
        commands = self.extract_commands(response)
        
        # If no commands were found but git commands are mentioned in backticks,
        # try to get a new response with proper formatting
        if not commands and '`git' in response:
            print("Retrying with proper command formatting...")
            response = chain.invoke(repo_info)
            commands = self.extract_commands(response)
        
        return response, commands 