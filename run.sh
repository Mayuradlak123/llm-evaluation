#!/bin/bash
echo "Starting AI Evaluation Pipeline (Monolithic Mode)..."

# Ensure environment variables are loaded
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the FastAPI app directly
python main.py
