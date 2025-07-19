# GitAgent PyPI Publishing Guide

## Overview

This guide helps you publish your GitAgent as a Python package on PyPI with MongoDB integration for user management using modern Python packaging standards.

## What We've Added

### 1. Package Structure (Kept Your Existing Structure!)
```
your-project/
├── pyproject.toml        # Modern PyPI package configuration (PEP 621)
├── MANIFEST.in           # Package file inclusion rules
├── LICENSE               # MIT License
├── cli.py                # New CLI entry point
├── setup_user.py         # User setup script
├── services/
│   ├── mongodb_service.py    # NEW: MongoDB integration
│   ├── groq_api_service.py   # Your existing service
│   └── git_service.py        # Your existing service
├── utils/                # Your existing utilities
├── controllers/          # Your existing controllers
├── git_agent_langgraph.py    # Your main functionality
└── requirements.txt      # Updated with new dependencies
```

### 2. New Features Added
- **MongoDB User Management**: Stores user email, creation/update timestamps, and API keys
- **Post-installation Setup**: Automatically prompts users for email after installation
- **Global CLI Command**: Users can run `gitagent` from anywhere
- **Secure API Key Management**: API keys are stored in MongoDB, not exposed in code
- **Modern Packaging**: Uses `pyproject.toml` (PEP 621) instead of legacy `setup.py`

## Why pyproject.toml?

✅ **Modern Standard**: `pyproject.toml` is the current Python packaging standard
✅ **Cleaner**: All configuration in one declarative file
✅ **Better Tool Support**: Works seamlessly with modern tools like `build`, `twine`, etc.
✅ **Future-Proof**: Actively maintained and supported by the Python community

## Publishing Steps

### Step 1: Setup PyPI Account
1. Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [Test PyPI](https://test.pypi.org/account/register/) (testing)

2. Generate API tokens:
   - Go to Account Settings → API tokens
   - Create tokens for both accounts
   - Save them securely

### Step 2: Install Publishing Tools
```bash
# Install modern build tools
pip install build twine

# Or install with dev dependencies (recommended)
pip install -e ".[dev]"
```

### Step 3: Configure Twine (Secure Upload)
Create `~/.pypirc`:
```ini
[distutils]
index-servers = 
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

### Step 4: Test Locally
```bash
# Install in development mode
pip install -e .

# Test the CLI
python cli.py --setup  # This will run user setup
python cli.py "test query"
```

### Step 5: Build Package (Modern Way)
```bash
# Clean any old builds
rm -rf dist/ build/ *.egg-info/

# Build with modern tools
python -m build

# Check the package
twine check dist/*
```

### Step 6: Publish to Test PyPI First
```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*
```

### Step 7: Test Installation from Test PyPI
```bash
# Test install from Test PyPI
pip install -i https://test.pypi.org/simple/ gitagent-ai

# Test the commands
gitagent-setup  # Setup user
gitagent "What's the git status?"  # Test functionality
```

### Step 8: Publish to Production PyPI
```bash
# When everything works, publish to production
twine upload dist/*
```

## Modern Build Commands Summary

### Building
```bash
# Build source and wheel distributions
python -m build

# Build only wheel
python -m build --wheel

# Build only source distribution
python -m build --sdist
```

### Publishing
```bash
# Check before upload
twine check dist/*

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Upload to PyPI (production)
twine upload dist/*
```

### Version Management
```bash
# Update version in pyproject.toml
[project]
version = "1.0.1"  # Increment for updates

# Then rebuild and republish
python -m build
twine upload dist/*
```

## User Experience After Installation

### 1. Installation
```bash
pip install gitagent-ai
```

### 2. First-time Setup
```bash
gitagent-setup
```

This will:
- Detect their git email or ask for it
- Store user info in your MongoDB database
- Create local configuration
- Show setup completion

### 3. Usage
```bash
# From any git repository
gitagent "What files have changed?"
gitagent "Create a new branch called feature-xyz"
gitagent --auto-approve "Stage all changes and commit"
```

## MongoDB Database Structure

### Collection: Users
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "createdAt": ISODate,
  "updatedAt": ISODate,
  "apiKey": "your-api-key-here"  // You'll set this manually
}
```

## Development Workflow

### Local Development
```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Format code (if using black)
black .

# Lint code (if using flake8)
flake8 .

# Test locally
python cli.py --setup
```

### Publishing Updates
```bash
# 1. Update version in pyproject.toml
# 2. Build package
python -m build

# 3. Test on Test PyPI first
twine upload --repository testpypi dist/*

# 4. Test installation
pip install -i https://test.pypi.org/simple/ gitagent-ai==NEW_VERSION

# 5. If all good, publish to production
twine upload dist/*
```

## Security Notes

### ✅ What's Secure:
- MongoDB connection string is hardcoded (for now) but not exposed to users
- API keys are stored in MongoDB, not in user's local files
- PyPI upload uses secure token authentication
- Modern packaging tools with better security

### ⚠️ Important Security Tasks:
1. **Move MongoDB credentials to environment variables** (recommended for production)
2. **Set up API key management system** for your users
3. **Consider rate limiting** for your MongoDB connections

## Environment Variables (Recommended)
Add to your environment or `.env` file:
```bash
MONGODB_CONNECTION_STRING="mongodb+srv://root:root@learningmongo.cr2lsf3.mongodb.net/"
MONGODB_DATABASE_NAME="GitAgent"
MONGODB_COLLECTION_NAME="Users"
```

## Monitoring Users

You can monitor user registrations directly in your MongoDB database:
```javascript
// MongoDB query to see all users
db.Users.find({}).sort({createdAt: -1})

// Count of users
db.Users.count()

// Users without API keys
db.Users.find({apiKey: ""})
```

## Support Workflow

When users contact you for API keys:
1. Verify their email in the MongoDB database
2. Generate/assign an API key
3. Update their record:
```javascript
db.Users.updateOne(
  {email: "user@example.com"}, 
  {$set: {apiKey: "their-new-api-key", updatedAt: new Date()}}
)
```

## Ready to Publish?

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test, then upload to production
twine upload dist/*
```

## Advantages of This Modern Approach

✅ **Standardized**: Uses PEP 621 standard
✅ **Cleaner**: Single configuration file
✅ **Better Tooling**: Works with all modern Python tools
✅ **Maintainable**: Easier to read and modify
✅ **Future-Ready**: Officially supported approach 