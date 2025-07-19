#!/usr/bin/env python3
"""
GitAgent CLI Entry Point
"""

import os
import sys
import argparse
from typing import Optional
from setup_user import load_user_config
from services.mongodb_service import MongoDBService


def check_user_setup() -> Optional[str]:
    """Check if user is properly set up"""
    email = load_user_config()
    if not email:
        print("❌ GitAgent is not set up yet.")
        print("Please run: gitagent-setup")
        return None
    
    return email


def check_api_key(email: str) -> bool:
    """Check if user has a valid API key"""
    mongo_service = MongoDBService()
    
    if not mongo_service.connect():
        print("⚠️  Cannot verify API key status (connection issue)")
        print("This may be a temporary network issue.")
        print("Please try again later or contact support if the problem persists.")
        return False  # Changed: Don't proceed if we can't verify
    
    try:
        has_key = mongo_service.has_valid_api_key(email)
        if not has_key:
            print("❌ Your API key is not configured.")
            print("Please contact support to get your API key activated.")
            print("GitAgent cannot function without a valid API key.")
        return has_key
    finally:
        mongo_service.disconnect()


def check_git_repository():
    """Check if we're in a git repository"""
    if not os.path.exists(".git"):
        print("❌ Not in a Git repository.")
        print("Please run this command from a Git repository root.")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="GitAgent - AI-powered Git assistant with persistent context"
    )
    parser.add_argument("query", nargs="*", help="Your query for the Git agent")
    parser.add_argument(
        "--auto-approve", "-y", 
        action="store_true", 
        help="Automatically approve all commands"
    )
    parser.add_argument(
        "--setup", 
        action="store_true", 
        help="Run user setup"
    )
    
    args = parser.parse_args()
    
    # Handle setup command
    if args.setup:
        from setup_user import setup_user
        setup_user()
        return
    
    # Check if we're in a git repository
    check_git_repository()
    
    # Check user setup
    email = check_user_setup()
    if not email:
        sys.exit(1)
    
    # Check API key status - MUST have valid key to proceed
    if not check_api_key(email):
        print("\n" + "="*60)
        print("🔒 ACCESS DENIED")
        print("="*60)
        print("GitAgent requires a valid API key to function.")
        print("This is necessary to access AI services and ensure quality responses.")
        print("\n📧 To get your API key activated:")
        print("1. Contact support with your registered email")
        print("2. Once activated, run GitAgent again")
        print(f"\nYour registered email: {email}")
        sys.exit(1)
    
    # Get query
    if args.query:
        query = " ".join(args.query)
    else:
        query = input("What would you like to do with your Git repository? ")
    
    if not query:
        print("❌ No query provided.")
        sys.exit(1)
    
    # Import and run the existing GitAgent
    try:
        from git_agent_langgraph import UnifiedGitAgent
        
        print("✅ API key verified. Initializing GitAgent...")
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
                
    except Exception as e:
        print(f"❌ Error running GitAgent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 