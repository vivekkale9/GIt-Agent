# Troubleshooting GitAgent

This document provides solutions to common issues you might encounter when using GitAgent.

## Installation Issues

### Ollama Installation

If you're having trouble installing Ollama:

1. Visit the official Ollama website: https://ollama.ai/download
2. Follow the platform-specific installation instructions
3. Verify installation with: `ollama --version`

### Model Download Issues

If you encounter errors downloading the Llama 2 model:

1. Ensure you have a stable internet connection
2. Try downloading a smaller model first: `ollama pull tinyllama`
3. Check your disk space: `df -h`
4. If you're behind a proxy, configure your environment variables accordingly

### Python Dependency Issues

If you encounter errors installing dependencies:

1. Ensure you have Python 3.8+ installed: `python --version`
2. Consider using a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Update pip: `pip install --upgrade pip`
4. Install dependencies one by one to identify problematic packages

## Runtime Issues

### Not in a Git Repository Error

If you see "Not in a Git repository" error:

1. Ensure you're running GitAgent from a Git repository root
2. If needed, initialize a Git repository: `git init`

### LLM Connection Issues

If GitAgent can't connect to the Ollama service:

1. Ensure Ollama is running: `ollama serve`
2. Check if the Ollama service is available: `curl http://localhost:11434/api/version`
3. If using a custom Ollama endpoint, verify its configuration

### Command Execution Issues

If Git commands fail to execute:

1. Ensure Git is installed and in your PATH: `git --version`
2. Try running the commands manually to see detailed error messages
3. Check if you have the necessary permissions to execute Git commands

## Alternative Models

If you want to use a different local model:

1. Download an alternative model: `ollama pull mistral` or `ollama pull orca-mini`
2. Modify the model name in `main.py` or `git_agent_langgraph.py`:
   ```python
   # Change this line:
   self.llm = Ollama(model="llama2")
   
   # To:
   self.llm = Ollama(model="mistral")  # or any other model you downloaded
   ```

## Performance Optimization

If GitAgent is running slowly:

1. Use a smaller model: `ollama pull tinyllama` or `ollama pull orca-mini`
2. Reduce the amount of Git history being processed:
   ```python
   # Change this line in main.py or git_agent_langgraph.py:
   def get_git_log(num_entries: int = 5) -> str:
   
   # To reduce the number of entries:
   def get_git_log(num_entries: int = 3) -> str:
   ```

## Using Other LLM Providers

GitAgent can be adapted to use other LLM providers. For example, to use OpenAI models:

1. Install the required package: `pip install langchain-openai`
2. Modify the LLM configuration in your code:
   ```python
   # Replace:
   from langchain_community.llms.ollama import Ollama
   self.llm = Ollama(model="llama2")
   
   # With:
   import os
   from langchain_openai import ChatOpenAI
   os.environ["OPENAI_API_KEY"] = "your-api-key"
   self.llm = ChatOpenAI(model="gpt-3.5-turbo")
   ```

## Getting Help

If you continue to experience issues:

1. Check the existing GitHub issues for similar problems
2. Create a detailed bug report with the following information:
   - Your operating system and version
   - Python version: `python --version`
   - Git version: `git --version`
   - Ollama version: `ollama --version`
   - The exact command you're running
   - The complete error message
   - Any relevant logs 