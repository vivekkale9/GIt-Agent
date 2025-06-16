import os
import sys
from controllers.git_controller import GitController

def handle_git_query(query: str) -> str:
    if not os.path.exists(".git"):
        return "Error: Not in a Git repository. Please run this command from a Git repository root."
    
    controller = GitController()
    return controller.handle_query(query) 