#!/usr/bin/env python3

import argparse
import os
import sys
from git_agent_langgraph import UnifiedGitAgent

def main():
    parser = argparse.ArgumentParser(description="GitAgent - Unified AI-powered Git assistant with persistent context")
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
