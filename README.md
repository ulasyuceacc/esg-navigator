# ESG Navigator

A web application powered by Google's NotebookLM via MCP, providing streaming answers with a modern, glassmorphic UI.

## Features
- Ask long context questions from a source vector of 45+ YouTube videos without token exhaustion.
- Typewriter-style live streaming of AI answers.
- Intelligent Suggested Topics loaded dynamically right from NotebookLM.
- "Always-on" stateful underlying MCP Server for blazing fast generation.

## How to Run
Ensure NotebookLM MCP server is installed and authenticated via `notebooklm-mcp-auth`.
Then run:
`python app.py`
Access `http://localhost:8080/`
