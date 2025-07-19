import requests
import json
import time
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Import configuration
from .config import GROQ_CONFIG

# Load environment variables from .env file
load_dotenv()

@dataclass
class GroqAPIKey:
    key: str
    is_exhausted: bool = False
    last_error_time: Optional[float] = None

class GroqAPIService:
    def __init__(self):
        # Load API keys using config file with environment variable fallbacks
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        
        # Load base URL and model with environment variable fallbacks
        self.base_url = os.getenv("GROQ_BASE_URL") or GROQ_CONFIG.get("base_url", "")
        self.model = os.getenv("GROQ_MODEL") or GROQ_CONFIG.get("model", "")
        
        # Validate that we have at least one API key
        if not self.api_keys:
            raise ValueError(
                "No Groq API keys found in configuration or environment variables."
            )
    
    def _load_api_keys(self) -> List[GroqAPIKey]:
        """Load API keys from environment variables first, then config file."""
        keys = []
        
        # First try to load from environment variables (development)
        key_index = 1
        while True:
            key_name = f"GROQ_API_KEY_{key_index}"
            api_key = os.getenv(key_name)
            
            if api_key:
                keys.append(GroqAPIKey(api_key))
                key_index += 1
            else:
                break
        
        # If no environment variables found, use config file (PyPI package)
        if not keys and GROQ_CONFIG.get("api_keys"):
            for api_key in GROQ_CONFIG["api_keys"]:
                keys.append(GroqAPIKey(api_key))
        
        return keys
    
    def get_next_available_key(self) -> Optional[GroqAPIKey]:
        """Get the next available API key, rotating through all keys."""
        attempts = 0
        while attempts < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            
            # Reset exhausted keys after 1 hour
            if key.is_exhausted and key.last_error_time:
                if time.time() - key.last_error_time > 3600:  # 1 hour
                    key.is_exhausted = False
                    key.last_error_time = None
            
            if not key.is_exhausted:
                return key
            
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            attempts += 1
        
        return None  # All keys are exhausted
    
    def mark_key_exhausted(self, key: GroqAPIKey):
        """Mark a key as exhausted."""
        key.is_exhausted = True
        key.last_error_time = time.time()
        print(f"API key ending in ...{key.key[-4:]} marked as exhausted")
    
    def make_api_call(self, messages: List[Dict], max_retries: int = 3) -> Optional[str]:
        """Make API call to Groq with automatic key rotation."""
        for attempt in range(max_retries):
            api_key = self.get_next_available_key()
            
            if not api_key:
                print("All API keys are exhausted. Please wait or add more keys.")
                return None
            
            headers = {
                "Authorization": f"Bearer {api_key.key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200: 
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                elif response.status_code == 429:  # Rate limit exceeded
                    print(f"Rate limit exceeded for key ending in ...{api_key.key[-4:]}")
                    self.mark_key_exhausted(api_key)
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    continue
                elif response.status_code == 401:  # Invalid API key
                    print(f"Invalid API key ending in ...{api_key.key[-4:]}")
                    self.mark_key_exhausted(api_key)
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    continue
                else:
                    print(f"API call failed with status {response.status_code}: {response.text}")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except requests.exceptions.RequestException as e:
                print(f"Request exception: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def generate_response(self, prompt: str, context: Dict = None) -> Optional[str]:
        """Generate a response using Groq API."""
        messages = [
            {
                "role": "system",
                "content": "You are GitAgent, an AI assistant specialized in Git operations. Analyze the repository state and provide helpful Git command suggestions."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        return self.make_api_call(messages) 