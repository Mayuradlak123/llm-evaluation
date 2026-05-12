#!/bin/bash

echo "Starting setup for LLM Evaluation App..."

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Setup complete!"

# Ask user if they want to run the app
read -p "Do you want to start the application now? (y/n): " choice
if [[ $choice == "y" || $choice == "Y" ]]; then
    echo "Launching application..."
    ./run.sh
else
    echo "You can start the app later using ./run.sh"
fi
