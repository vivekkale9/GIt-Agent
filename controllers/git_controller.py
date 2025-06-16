from typing import Dict, List, Tuple
from services.git_service import GitService

class GitController:
    def __init__(self):
        self.git_service = GitService()
    
    def handle_query(self, query: str) -> str:
        response, executed_commands = self.git_service.process_query(query)
        
        if executed_commands:
            print("\n📋 Summary of Actions Taken:")
            for i, cmd in enumerate(executed_commands, 1):
                print(f"{i}. {cmd}")
        
        return response 