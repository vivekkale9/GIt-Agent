#!/usr/bin/env python3
"""
GitAgent User Setup Script
This script runs after installation to set up the user profile
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional
from services.mongodb_service import MongoDBService


def get_git_user_email() -> Optional[str]:
    """Get the git user email from git config"""
    try:
        result = subprocess.run(['git', 'config', '--global', 'user.email'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_user_config_dir() -> Path:
    """Get the user's configuration directory"""
    try:
        if sys.platform == "win32":
            # Windows: Use APPDATA
            config_dir = Path(os.environ.get("APPDATA", "")) / "GitAgent"
        else:
            # macOS/Linux: Try ~/.config/gitagent first
            config_dir = Path.home() / ".config" / "gitagent"
        
        # Try to create the directory
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Test if we can write to it
        test_file = config_dir / ".test"
        test_file.write_text("test")
        test_file.unlink()
        
        return config_dir
        
    except (OSError, PermissionError):
        # Fallback: Use a directory in user's home
        fallback_dir = Path.home() / ".gitagent"
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir
        except (OSError, PermissionError):
            # Final fallback: Use current directory
            fallback_dir = Path.cwd() / ".gitagent"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir


def save_user_config(email: str):
    """Save user configuration to local file"""
    try:
        config_dir = get_user_config_dir()
        config_file = config_dir / "user.config"
        
        with open(config_file, 'w') as f:
            f.write(f"email={email}\n")
        
        print(f"📁 Configuration saved to: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save user configuration: {e}")
        print("⚠️  You may need to run setup again or check file permissions.")
        return False


def load_user_config() -> Optional[str]:
    """Load user email from local configuration"""
    # Try multiple locations
    possible_locations = []
    
    try:
        if sys.platform == "win32":
            possible_locations.append(Path(os.environ.get("APPDATA", "")) / "GitAgent" / "user.config")
        else:
            possible_locations.append(Path.home() / ".config" / "gitagent" / "user.config")
        
        possible_locations.append(Path.home() / ".gitagent" / "user.config")
        possible_locations.append(Path.cwd() / ".gitagent" / "user.config")
    except Exception:
        pass
    
    for config_file in possible_locations:
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    content = f.read().strip()
                    if content.startswith("email="):
                        return content.split("=", 1)[1]
            except Exception:
                continue
    
    return None


def setup_user():
    """Main setup function"""
    print("\n" + "="*60)
    print("🚀 Welcome to GitAgent Setup!")
    print("="*60)
    
    # Check if user is already configured
    existing_email = load_user_config()
    if existing_email:
        print(f"✅ You're already configured with email: {existing_email}")
        
        reconfigure = input("Would you like to reconfigure? (y/N): ").lower().strip()
        if reconfigure not in ['y', 'yes']:
            print("Setup completed!")
            return
    
    # Get git user email as suggestion
    git_email = get_git_user_email()
    
    print("\n📧 GitAgent needs your email to associate with your usage.")
    print("This will be stored securely and used for service management.")
    
    if git_email:
        print(f"\n💡 We found your git email: {git_email}")
        use_git_email = input("Use this email? (Y/n): ").lower().strip()
        
        if use_git_email not in ['n', 'no']:
            email = git_email
        else:
            email = input("\nEnter your email: ").strip()
    else:
        email = input("\nEnter your email: ").strip()
    
    # Validate email
    if not is_valid_email(email):
        print("❌ Invalid email format. Please run 'gitagent-setup' again.")
        sys.exit(1)
    
    print(f"\n🔄 Setting up GitAgent for {email}...")
    
    # Connect to MongoDB and create/update user
    mongo_service = MongoDBService()
    
    print("📡 Connecting to GitAgent services...")
    if not mongo_service.connect():
        print("\n" + "="*60)
        print("❌ SETUP FAILED - CONNECTION ISSUE")
        print("="*60)
        print("Unable to connect to GitAgent services.")
        print("\n🔧 What you can do:")
        print("1. ✅ Your email has been saved locally")
        print("2. 🔄 Try running 'gitagent-setup' again later")
        print("3. 📧 Contact support if the issue persists")
        print("4. 🌐 Check if you're on a corporate network with restrictions")
        print("\n📝 Your information:")
        print(f"   Email: {email}")
        print("   Status: Saved locally, pending server registration")
        
        # Still save the config locally
        save_user_config(email)
        
        print("\n⚠️  You can use GitAgent once the connection issue is resolved.")
        print("Your email is saved and will be used when services are available.")
        sys.exit(1)
    
    try:
        # Check if user exists
        if mongo_service.user_exists(email):
            print("✅ User already exists in our database.")
            
            if mongo_service.has_valid_api_key(email):
                print("✅ Your API key is configured and ready!")
            else:
                print("⚠️  Your API key is not configured yet.")
                print("Please contact support to get your API key activated.")
        else:
            print("📝 Creating new user profile...")
            if mongo_service.create_user(email):
                print("✅ User profile created successfully!")
                print("⚠️  Your API key is not configured yet.")
                print("Please contact support:vivekskale03@gmail.com to get your API key activated.")
            else:
                print("❌ Failed to create user profile.")
                sys.exit(1)
        
        # Save configuration locally
        if save_user_config(email):
            print("✅ Local configuration saved.")
        else:
            print("⚠️  Failed to save local configuration.")
            print("GitAgent will still work, but you may need to run setup again.")
        
    finally:
        mongo_service.disconnect()
    
    print("\n" + "="*60)
    print("🎉 GitAgent Setup Complete!")
    print("="*60)
    print("You can now use 'gitagent' command from any git repository!")
    print("\nExamples:")
    print('  gitagent "What files have changed?"')
    print('  gitagent "Create a new branch called feature-xyz"')
    print('  gitagent "Stage all changes and commit with message"')
    print("\n💡 Note: You'll need an active API key to use GitAgent.")
    print("If you don't have one yet, please contact support.")


if __name__ == "__main__":
    setup_user() 