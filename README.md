# GitAgent - AI-Powered Git Assistant

GitAgent is a command-line tool that uses AI to help you manage your Git repositories. It understands natural language queries and can execute Git commands on your behalf.

## Features

- Natural language interface for Git operations
- Intelligent command suggestions based on repository state
- Safe execution with user confirmation
- Detailed execution summaries
- Error handling and conflict detection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gitagent.git
cd gitagent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure you have Ollama installed and the llama2 model downloaded:
```bash
ollama pull llama2
```

## Usage

You can use GitAgent in two ways:

1. With a direct query:
```bash
python main.py "create a new branch called feature/login"
```

2. Interactive mode:
```bash
python main.py
```

## Project Structure

The project follows a modular architecture:

```
gitagent/
├── main.py                 # Entry point
├── routes.py              # Request routing
├── controllers/
│   └── git_controller.py  # User interaction handling
├── services/
│   └── git_service.py     # Business logic
└── utils/
    ├── git_commands.py    # Git command utilities
    └── prompt_templates.py # AI prompt templates
```

## Example Queries

- "Show me my unpushed commits"
- "Create a new branch called feature/login"
- "Merge the develop branch into main"
- "What changes have I made but not committed?"
- "Push my changes to origin"

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 