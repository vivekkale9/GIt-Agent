#!/usr/bin/env python3

"""
GitAgent Demo Script

This script provides a guided demonstration of GitAgent's capabilities.
It showcases various example queries and explains the different features.
"""

import os
import time
import subprocess
import sys

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_section(title):
    """Print a section title."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def print_slowly(text, delay=0.03):
    """Print text with a typewriter effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def wait_for_key():
    """Wait for the user to press a key."""
    print("\nPress Enter to continue...", end='', flush=True)
    input()

def run_demo_command(command, description, show_output=True):
    """Run a demo command and show its output."""
    print_section(description)
    print_slowly(f"Running: {command}")
    print()
    
    if show_output:
        # Actually execute the command
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end='')
        process.wait()
    else:
        # Just show what would be executed
        print_slowly("(Command execution skipped in demo mode)")
    
    wait_for_key()

def main():
    clear_screen()
    
    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a Git repository. Please run this demo from a Git repository root.")
        sys.exit(1)
    
    print_section("Welcome to GitAgent Demo")
    print_slowly("GitAgent is an AI-powered assistant for Git repositories.")
    print_slowly("This demo will show you various ways to use GitAgent.")
    print_slowly("You'll see example queries and commands to try.")
    wait_for_key()
    
    # Basic information queries
    print_section("Basic Information Queries")
    print_slowly("GitAgent can provide information about your repository.")
    print_slowly("\nExamples:")
    print_slowly("1. What's the status of my repository?")
    print_slowly("2. Show me my branches")
    print_slowly("3. What changes have I made but not committed?")
    
    run_demo_command("./gitagent 'What is the status of my repository?'", 
                    "Example 1: Repository Status", show_output=True)
    
    # Git operations
    print_section("Git Operations")
    print_slowly("GitAgent can recommend and execute Git commands.")
    print_slowly("\nExamples:")
    print_slowly("1. How do I stage all my changes?")
    print_slowly("2. How do I commit my changes with a message?")
    print_slowly("3. How do I push my changes to the remote repository?")
    
    run_demo_command("./gitagent 'How do I stage all my modified files?'", 
                    "Example 2: Staging Changes", show_output=True)
    
    # Advanced workflows
    print_section("Advanced Workflows")
    print_slowly("GitAgent can help with more complex Git workflows.")
    print_slowly("\nExamples:")
    print_slowly("1. How do I create a new branch and switch to it?")
    print_slowly("2. How do I merge the develop branch into main?")
    print_slowly("3. How do I rebase my branch onto main?")
    
    run_demo_command("./gitagent -a 'How do I create a new branch called feature/new-login?'", 
                    "Example 3: Branch Creation (Advanced Mode)", show_output=True)
    
    # Troubleshooting
    print_section("Troubleshooting")
    print_slowly("GitAgent can help solve common Git problems.")
    print_slowly("\nExamples:")
    print_slowly("1. How do I undo my last commit?")
    print_slowly("2. How do I resolve merge conflicts?")
    print_slowly("3. How do I fix a detached HEAD state?")
    
    run_demo_command("./gitagent -a 'How can I undo my last commit but keep the changes?'", 
                    "Example 4: Undoing Commits (Advanced Mode)", show_output=True)
    
    # Conclusion
    print_section("Thank you for trying GitAgent!")
    print_slowly("You've seen some examples of what GitAgent can do.")
    print_slowly("Remember, you can ask any Git-related question in natural language.")
    print_slowly("\nUsage:")
    print_slowly("  ./gitagent \"your question here\"     # Basic mode")
    print_slowly("  ./gitagent -a \"your question here\"  # Advanced mode")
    print_slowly("\nHappy coding!")

if __name__ == "__main__":
    main() 