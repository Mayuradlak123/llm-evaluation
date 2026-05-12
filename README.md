# FastAPI + LangSmith Evaluation App

A simple FastAPI application integrated with LangSmith for tracing and evaluating LLM calls.

## Features
- **FastAPI**: Modern Python web framework.
- **LangGraph**: State-based agentic workflow.
- **Groq**: High-performance LLM inference.
- **Jinja2**: Template engine for HTML.
- **Tailwind CSS**: Premium UI with glassmorphism design.
- **LangSmith Integration**: Automatic tracing of LangGraph workflows.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Update the `.env` file with your API keys:
   - `GROQ_API_KEY`: Your Groq API key.
   - `LANGCHAIN_API_KEY`: Your LangSmith API key.

3. **Run the Application**:
   You can use the provided shell scripts for easy setup and execution:
   ```bash
   # First time setup
   ./setup.sh

   # Start the app
   ./run.sh
   ```
   Or manually:
   ```bash
   python main.py
   ```

4. **Access the UI**:
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## LangSmith Tracing
Once you submit a query, the trace will automatically be sent to your LangSmith project specified in the `.env` file (`fastapi-eval-app`).
