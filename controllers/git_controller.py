from typing import Dict, List, Tuple
from services.git_service import GitService

class GitController:
    def __init__(self):
        self.git_service = GitService()
    
    def handle_query(self, query: str) -> str:
        """Handle a user query and return the final response."""
        # Get AI response and suggested commands
        response, commands = self.git_service.process_query(query)
        
        # If there are commands to execute, ask for confirmation
        if commands:
            print("\nI recommend the following workflow to complete your request:")
            for i, cmd in enumerate(commands, 1):
                print(f"Step {i}: {cmd}")
            
            confirmation = input("\nDo you want me to execute these commands? (yes/no): ").lower()
            if confirmation in ["yes", "y"]:
                # Execute commands and get results
                results = self.git_service.execute_commands(commands)
                
                # Generate execution summary
                summary = "\n\nExecution Results:\n"
                for i, (cmd, result) in enumerate(results, 1):
                    summary += f"Step {i}: git {cmd}\nResult: {result}\n\n"
                
                return response + summary
            else:
                return response + "\n\nCommands were not executed per your request."
        
        return response 