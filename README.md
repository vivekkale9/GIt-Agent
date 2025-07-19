# GitAgent - Unified AI-Powered Git Assistant

**GitAgent** is a unified AI-powered Git assistant that provides intelligent, context-aware Git operations with persistent session management and automatic command verification.


## 🚀 Key Features

### 📝 **Persistent Context Management**
- **Session persistence** across multiple invocations
- **Workflow resumption** for interrupted operations  
- **Command history** and verification tracking

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


## 🛠️ Installation

1. **Install the package:**
   ```bash
   pip install gitagent-ai
   ```

3. **Setup User:**
   ```bash
   gitagent-setup
   ```

4. **Set up your Groq API key** (currently need to contact admin : vivekskale03@gmail.com):


## 📖 Usage

```bash
# Interactive mode - ask any Git question
gitagent "What's the current status of my repository?"

# Multi-step operations
gitagent "Stage all changes, commit with a meaningful message, and push to origin"

# Branch operations  
gitagent "Delete current branch and create a new feature branch called user-auth"
```


## 🔧 Architecture

### Unified Agent Design
- **Single LangGraph workflow** handles all scenarios
- **State management** with persistent sessions
- **Command verification** at each step
- **Intelligent routing** based on context and intent

### Session Persistence
- Full command history with verification results
- Workflow context and step tracking
- Resumable across GitAgent invocations

### Verification System
- **Pre-execution** prerequisite checking
- **Post-execution** state verification
- **Semantic validation** of command outcomes
- **Detailed error reporting** with recovery suggestions


## 🆘 Support

If you encounter any issues or have questions:
Contact support : vivekskale03@gmail.com

---

**GitAgent** - Intelligent Git assistance with persistent context and reliable execution tracking.
