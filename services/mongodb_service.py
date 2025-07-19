"""
MongoDB service for GitAgent user management
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import dotenv
from .config import MONGODB_CONFIG

class MongoDBService:
    """Service for managing GitAgent users in MongoDB"""
    
    def __init__(self):
        # Load environment variables (works in development with .env file)
        dotenv.load_dotenv()
        
        # Priority order:
        # 1. Environment variables (development/deployment)
        # 2. Config file (PyPI package)
        # 3. Empty string (will cause error - better than silent failure)
        self.connection_string = (
            os.getenv("MONGO_URI") or 
            MONGODB_CONFIG.get("connection_string") or 
            ""
        )
        self.database_name = (
            os.getenv("DB") or 
            MONGODB_CONFIG.get("database_name") or 
            "GitAgent"
        )
        self.collection_name = (
            os.getenv("COLLECTION") or 
            MONGODB_CONFIG.get("collection_name") or 
            "Users"
        )
        
        # Validate configuration
        if not self.connection_string:
            raise ValueError("MongoDB connection string not found. Check your configuration.")
        
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """Connect to MongoDB with SSL fallback options"""
        # Try different SSL configurations for maximum compatibility
        ssl_configs = [
            # Default SSL (most secure - works for most users)
            {},
            # Corporate network friendly (bypass certificate validation)
            {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": True
            },
            # Maximum compatibility (bypass all TLS validation)
            {
                "tls": True,
                "tlsInsecure": True
            },
            # Alternative with specific TLS version
            {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "ssl_cert_reqs": 0  # ssl.CERT_NONE equivalent
            }
        ]
        
        for i, ssl_config in enumerate(ssl_configs):
            try:
                print(f"🔄 Attempting connection (method {i+1}/{len(ssl_configs)})...")
                
                self.client = MongoClient(
                    self.connection_string,
                    serverSelectionTimeoutMS=8000,   # Increased timeout for slower networks
                    connectTimeoutMS=15000,          # Increased timeout for slower networks
                    socketTimeoutMS=15000,           # Increased timeout for slower networks
                    retryWrites=True,                # Enable retryable writes
                    maxPoolSize=10,                  # Limit connection pool size
                    **ssl_config
                )
                
                # Test the connection with a more robust ping
                self.client.admin.command('ping')
                
                # Verify database and collection access
                self.db = self.client[self.database_name]
                self.collection = self.db[self.collection_name]
                
                # Test collection access
                self.collection.find_one({}, {"_id": 1})
                
                print("✅ Successfully connected to MongoDB!")
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                if i == len(ssl_configs) - 1:  # Last attempt
                    print(f"❌ Failed to connect to MongoDB after all attempts.")
                    print("🌐 Network Connectivity Issues Detected")
                    print("This could be due to:")
                    print("  • Corporate firewall blocking MongoDB Atlas (port 27017)")
                    print("  • VPN or proxy interference")
                    print("  • Regional network restrictions")
                    print("  • DNS resolution issues")
                    print("  • SSL/TLS certificate verification problems")
                    print("\n💡 Quick fixes to try:")
                    print("  1. Try from a different network (mobile hotspot)")
                    print("  2. Check if you can access the internet normally")
                    print("  3. Temporarily disable VPN if using one")
                    print("  4. Contact your network admin about MongoDB Atlas access")
                    print("  5. If this persists, contact GitAgent support")
                    return False
                else:
                    print(f"⚠️  Method {i+1} failed (network/SSL issue), trying alternative...")
                    continue
                    
            except Exception as e:
                error_msg = str(e).lower()
                if "authentication" in error_msg:
                    print(f"❌ Database authentication failed. Please contact GitAgent support.")
                    return False
                elif "timeout" in error_msg:
                    if i == len(ssl_configs) - 1:
                        print(f"❌ Connection timeout. Your network may be blocking MongoDB access.")
                        return False
                    else:
                        print(f"⚠️  Method {i+1} timed out, trying alternative...")
                        continue
                else:
                    if i == len(ssl_configs) - 1:
                        print(f"❌ Unexpected error: {e}")
                        print("💬 Please report this error to GitAgent support")
                        return False
                    else:
                        print(f"⚠️  Method {i+1} failed: {e}")
                        continue
        
        return False
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.collection = None
    
    def user_exists(self, email: str) -> bool:
        """Check if user exists in database"""
        if self.collection is None:
            return False
        
        try:
            user = self.collection.find_one({"email": email})
            return user is not None
        except Exception as e:
            print(f"❌ Error checking user existence: {e}")
            return False
    
    def create_user(self, email: str, api_key: Optional[str] = None) -> bool:
        """Create a new user in the database"""
        if self.collection is None:
            return False
        
        try:
            user_data = {
                "email": email,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "apiKey": api_key or ""  # Will be manually set later
            }
            
            result = self.collection.insert_one(user_data)
            return result.inserted_id is not None
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data from database"""
        if self.collection is None:
            return None
        
        try:
            user = self.collection.find_one({"email": email})
            return user
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None
    
    def update_user(self, email: str, update_data: Dict[str, Any]) -> bool:
        """Update user data in database"""
        if self.collection is None:
            return False
        
        try:
            update_data["updatedAt"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"❌ Error updating user: {e}")
            return False
    
    def has_valid_api_key(self, email: str) -> bool:
        """Check if user has a valid API key"""
        user = self.get_user(email)
        if not user:
            return False
        
        api_key = user.get("apiKey", "")
        return api_key and api_key.strip() != ""