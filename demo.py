#!/usr/bin/env python3

"""
GitAgent Demo Script - Unified Implementation

This script provides a guided demonstration of GitAgent's new unified capabilities
including persistent context management, session handling, and command verification.
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
    
    print_section("Welcome to GitAgent Unified Demo")
    print_slowly("GitAgent is now a unified AI-powered assistant for Git repositories.")
    print_slowly("Key improvements in this version:")
    print_slowly("  • Persistent context across multiple sessions")
    print_slowly("  • Automatic command verification and success tracking")
    print_slowly("  • Intelligent multi-step workflow management")
    print_slowly("  • Session resumption for interrupted workflows")
    print_slowly("  • No separate basic/advanced modes - everything is unified!")
    wait_for_key()
    
    # Basic information queries with context
    print_section("1. Smart Information Queries")
    print_slowly("GitAgent now provides context-aware information with session memory.")
    print_slowly("\nFeatures:")
    print_slowly("  • Remembers previous queries and commands")
    print_slowly("  • Provides context-specific recommendations")
    print_slowly("  • Tracks repository state changes")
    
    run_demo_command("./gitagent 'What is the current state of my repository?'", 
                    "Example 1: Context-Aware Repository Status", show_output=True)
    
    # Multi-step workflows
    print_section("2. Intelligent Multi-Step Workflows")
    print_slowly("GitAgent can now handle complex multi-step operations with:")
    print_slowly("  • Automatic prerequisite checking")
    print_slowly("  • Command verification after execution")
    print_slowly("  • Error recovery and retry logic")
    print_slowly("  • Session persistence across interruptions")
    
    run_demo_command("./gitagent 'I want to stage all changes and commit them with a meaningful message'", 
                    "Example 2: Multi-Step Staging and Commit", show_output=True)
    
    # Session management demonstration
    print_section("3. Session Management and Persistence")
    print_slowly("GitAgent maintains persistent sessions that can be resumed:")
    print_slowly("  • Sessions are saved in .git/gitagent_sessions/")
    print_slowly("  • Workflows can be interrupted and resumed")
    print_slowly("  • Context is preserved across multiple invocations")
    print_slowly("  • Command history and verification results are tracked")
    
    # Show session files if they exist
    session_dir = ".git/gitagent_sessions"
    if os.path.exists(session_dir):
        session_files = os.listdir(session_dir)
        if session_files:
            print_slowly(f"\nCurrent session files: {len(session_files)}")
            for session_file in session_files[:3]:  # Show first 3
                print_slowly(f"  • {session_file}")
    
    wait_for_key()
    
    # Command verification
    print_section("4. Advanced Command Verification")
    print_slowly("Every command is now verified for success:")
    print_slowly("  • Automatic post-execution state checking")
    print_slowly("  • Semantic verification (not just error codes)")
    print_slowly("  • Detailed success/failure reporting")
    print_slowly("  • Intelligent error recovery suggestions")
    
    run_demo_command("./gitagent 'Show me how command verification works with a simple git status'", 
                    "Example 3: Command Verification Demo", show_output=True)
    
    # Auto-approve mode
    print_section("5. Auto-Approve Mode for Automation")
    print_slowly("For automation and CI/CD, use auto-approve mode:")
    print_slowly("  • All commands execute without user confirmation")
    print_slowly("  • Perfect for scripts and automated workflows")
    print_slowly("  • Still maintains full verification and error handling")
    
    run_demo_command("./gitagent -y 'Check repository status (auto-approved)'", 
                    "Example 4: Auto-Approve Mode", show_output=True)
    
    # Workflow resumption
    print_section("6. Workflow Resumption")
    print_slowly("If a workflow is interrupted, GitAgent can resume where it left off:")
    print_slowly("  • Run 'gitagent continue' to resume interrupted workflows")
    print_slowly("  • Or run any new command to continue previous context")
    print_slowly("  • Full session history is maintained and accessible")
    
    print_slowly("\nTry this yourself:")
    print_slowly("  1. Start a multi-step operation")
    print_slowly("  2. Cancel it midway (Ctrl+C)")
    print_slowly("  3. Run './gitagent continue' to resume")
    wait_for_key()
    
    # Conclusion
    print_section("GitAgent Unified - Ready for Production!")
    print_slowly("🎉 You've seen the new unified GitAgent capabilities!")
    print_slowly("\nKey benefits:")
    print_slowly("  ✅ No more confusion between basic/advanced modes")
    print_slowly("  ✅ Persistent context that survives interruptions")
    print_slowly("  ✅ Reliable command verification and error handling")
    print_slowly("  ✅ Intelligent multi-step workflow management")
    print_slowly("  ✅ Perfect for both interactive use and automation")
    
    print_slowly("\nUsage:")
    print_slowly("  ./gitagent \"your question here\"     # Interactive mode")
    print_slowly("  ./gitagent -y \"your question here\"  # Auto-approve mode")
    print_slowly("  ./gitagent continue                   # Resume workflow")
    print_slowly("  ./gitagent --help                     # Show all options")
    
    print_slowly("\n🚀 Happy coding with intelligent Git assistance!")

if __name__ == "__main__":
    main() 