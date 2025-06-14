#!/usr/bin/env python3

import sys
import os
import termios
import tty
import select
from typing import Optional

def get_confirmation(prompt: str, default_yes: bool = True) -> bool:
    """
    Get user confirmation with advanced input handling.
    
    Args:
        prompt: The confirmation prompt to display
        default_yes: Whether Enter should default to yes
    
    Returns:
        bool: True for yes, False for no
    
    Input options:
        - Enter: Default (yes if default_yes=True, no if default_yes=False)
        - Esc: No
        - y/yes + Enter: Yes
        - n/no + Enter: No
    """
    try:
        return _get_confirmation_with_shortcuts(prompt, default_yes)
    except (ImportError, OSError):
        # Fallback to simple input if keyboard shortcuts don't work
        return _get_confirmation_simple(prompt, default_yes)

def _get_confirmation_with_shortcuts(prompt: str, default_yes: bool) -> bool:
    """Advanced confirmation with keyboard shortcuts (Unix/Linux/Mac)."""
    if os.name != 'posix':
        # Fall back to simple input on Windows
        return _get_confirmation_simple(prompt, default_yes)
    
    print(f"{prompt}")
    print("Press Enter for YES, Esc for NO, or type 'yes'/'no' and press Enter")
    print("(Enter=yes, Esc=no, or type your choice): ", end="", flush=True)
    
    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        # Set terminal to raw mode
        tty.setraw(sys.stdin.fileno())
        
        input_buffer = ""
        
        while True:
            # Check if input is available
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                char = sys.stdin.read(1)
                
                # Handle special keys
                if char == '\r' or char == '\n':  # Enter key
                    if input_buffer.strip() == "":
                        # Empty input - use default
                        print("\n")
                        return default_yes
                    else:
                        # Process typed input
                        response = input_buffer.strip().lower()
                        print("\n")
                        return response in ['yes', 'y']
                
                elif char == '\x1b':  # Esc key
                    print("\n")
                    return False
                
                elif char == '\x7f' or char == '\b':  # Backspace
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        print('\b \b', end='', flush=True)
                
                elif char.isprintable():
                    input_buffer += char
                    print(char, end='', flush=True)
                
                elif char == '\x03':  # Ctrl+C
                    print("\n")
                    raise KeyboardInterrupt
    
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def _get_confirmation_simple(prompt: str, default_yes: bool) -> bool:
    """Simple confirmation fallback for systems without advanced keyboard support."""
    default_str = "YES" if default_yes else "NO"
    full_prompt = f"{prompt}\nPress Enter for {default_str}, or type 'yes'/'no': "
    
    while True:
        try:
            response = input(full_prompt).strip().lower()
            
            if response == "":
                # Empty input - use default
                return default_yes
            elif response in ["yes", "y"]:
                return True
            elif response in ["no", "n"]:
                return False
            else:
                print("Please enter 'yes', 'no', or just press Enter for default")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return False
        except EOFError:
            print("\nOperation cancelled.")
            return False 