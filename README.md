# GitAgent - Unified AI-Powered Git Assistant

**GitAgent** is a unified AI-powered Git assistant that provides intelligent, context-aware Git operations with persistent session management and automatic command verification.

## 🚀 Key Features

### 🧠 **Unified Intelligence**
- **No more basic/advanced modes** - All features unified in one intelligent system
- Context-aware command recommendations based on repository state
- Natural language understanding for complex Git operations

### 📝 **Persistent Context Management**
- **Session persistence** across multiple invocations
- **Workflow resumption** for interrupted operations  
- **Command history** and verification tracking
- Sessions stored in `.git/gitagent_sessions/` for full context preservation

### ✅ **Advanced Command Verification**
- **Automatic success verification** after each command execution
- **Semantic verification** beyond just error codes
- **Intelligent error recovery** with specific issue identification
- **Pre-execution prerequisite checking**

### 🔄 **Multi-Step Workflow Management**
- **Intelligent workflow decomposition** for complex operations
- **Step-by-step execution** with user confirmation
- **Context preservation** across workflow steps
- **Automatic workflow completion** tracking

### ⚡ **Automation Ready**
- **Auto-approve mode** (`-y` flag) for scripts and CI/CD
- **Full verification** even in automated mode
- **Detailed execution logging** and result tracking

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd GitAgent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Make the script executable:**
   ```bash
   chmod +x gitagent
   ```

4. **Set up your Groq API key** (required for AI functionality):
   ```bash
   export GROQ_API_KEY="your-groq-api-key"
   ```

## 📖 Usage

### Basic Usage
```bash
# Interactive mode - ask any Git question
./gitagent "What's the current status of my repository?"

# Multi-step operations
./gitagent "Stage all changes, commit with a meaningful message, and push to origin"

# Branch operations  
./gitagent "Delete current branch and create a new feature branch called user-auth"
```

### Auto-Approve Mode (for automation)
```bash
# Automatically approve all recommended commands
./gitagent -y "Stage and commit all changes"

# Perfect for scripts and CI/CD pipelines
./gitagent -y "Push all commits to origin main"
```

### Session Management
```bash
# Resume interrupted workflows
./gitagent continue

# Or just run any command - GitAgent will detect and offer to resume active sessions
./gitagent "What should I do next?"
```

### Help and Options
```bash
./gitagent --help
```

## 🎯 Example Workflows

### 1. **Smart Repository Analysis**
```bash
./gitagent "Analyze my repository and tell me what needs attention"
```
- Analyzes current status, uncommitted changes, unpushed commits
- Provides context-aware recommendations
- Remembers previous analysis for comparison

### 2. **Complex Branch Operations**
```bash
./gitagent "I want to delete this feature branch and create a new one for bug fixes"
```
- Automatically switches to safe branch before deletion
- Verifies branch deletion success
- Creates new branch with proper base
- Tracks entire workflow in session

### 3. **Commit Workflow Automation**
```bash
./gitagent -y "Stage modified files, create commit with descriptive message, and push"
```
- Intelligently stages appropriate files
- Generates meaningful commit messages
- Handles push with proper upstream tracking
- Verifies each step's success

### 4. **Error Recovery**
```bash
# If something goes wrong, GitAgent can help recover
./gitagent "The last command failed, what should I do?"
```
- Analyzes failure context from session history
- Provides specific recovery steps
- Can resume workflow after fixes

## 🔧 Architecture

### Unified Agent Design
- **Single LangGraph workflow** handles all scenarios
- **State management** with persistent sessions
- **Command verification** at each step
- **Intelligent routing** based on context and intent

### Session Persistence
- Sessions stored as JSON in `.git/gitagent_sessions/`
- Full command history with verification results
- Workflow context and step tracking
- Resumable across GitAgent invocations

### Verification System
- **Pre-execution** prerequisite checking
- **Post-execution** state verification
- **Semantic validation** of command outcomes
- **Detailed error reporting** with recovery suggestions

## 📂 Project Structure

```
GitAgent/
├── git_agent_langgraph.py    # Main unified agent implementation
├── gitagent                  # Executable script
├── main.py                   # Alternative entry point
├── demo.py                   # Interactive demonstration
├── services/
│   ├── git_service.py        # Legacy service (deprecated)
│   └── groq_api_service.py   # AI service integration
├── utils/
│   ├── git_commands.py       # Git command execution utilities
│   ├── input_handler.py      # User interaction handling
│   └── streaming.py          # Output formatting utilities
└── controllers/              # Legacy controllers (deprecated)
```

## 🚀 What's New in Unified Version

### ✅ **Fixed Issues**
- **Context persistence** - No more losing context between steps
- **Execution tracking** - Full visibility into what worked/failed
- **Session management** - Resume interrupted workflows
- **Command verification** - Reliable success/failure detection
- **Unified experience** - No confusion between basic/advanced modes

### 🆕 **New Capabilities**
- **Intelligent workflow decomposition** for complex requests
- **Automatic error recovery** with specific guidance
- **Session-based context** that survives interruptions
- **Advanced verification** beyond simple error checking
- **Production-ready automation** with auto-approve mode

## 🔍 Demo

Run the interactive demo to see all features:
```bash
python demo.py
```

The demo showcases:
- Context-aware information queries
- Multi-step workflow management
- Session persistence and resumption
- Command verification in action
- Auto-approve mode for automation

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues or have questions:
1. Check the demo for usage examples
2. Run `./gitagent --help` for options
3. Look in `.git/gitagent_sessions/` for session logs
4. Open an issue with session details for debugging

---

**GitAgent Unified** - Intelligent Git assistance with persistent context and reliable execution tracking.
