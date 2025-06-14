#!/usr/bin/env python3

import sys
import time
from typing import Optional

def stream_text(text: str, delay: float = 0.03, end: str = '\n', flush: bool = True) -> None:
    """
    Stream text character by character with a delay.
    
    Args:
        text: The text to stream
        delay: Delay between characters in seconds
        end: String appended after the text
        flush: Whether to flush output after each character
    """
    for char in text:
        print(char, end='', flush=flush)
        if char not in [' ', '\n']:  # Don't delay on spaces and newlines for better flow
            time.sleep(delay)
    print(end, end='')

def stream_lines(lines: list, line_delay: float = 0.02, char_delay: float = 0.01) -> None:
    """
    Stream multiple lines with delays between lines and characters.
    
    Args:
        lines: List of lines to stream
        line_delay: Delay between lines in seconds
        char_delay: Delay between characters in seconds
    """
    for i, line in enumerate(lines):
        if i > 0:
            time.sleep(line_delay)
        stream_text(line, delay=char_delay, end='')
    print()  # Final newline

def stream_formatted_text(text: str, delay: float = 0.02) -> None:
    """
    Stream text with smart formatting - faster for common words, slower for important parts.
    
    Args:
        text: The text to stream
        delay: Base delay between characters
    """
    # Common words that can be displayed faster
    fast_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'will', 'be', 'this', 'that'}
    
    words = text.split(' ')
    
    for i, word in enumerate(words):
        if i > 0:
            print(' ', end='', flush=True)
            
        # Determine speed based on word importance
        word_delay = delay * 0.3 if word.lower() in fast_words else delay
        
        for char in word:
            print(char, end='', flush=True)
            time.sleep(word_delay)
    
    print()  # Final newline 