#!/bin/bash

# Set up environment variables
export PAPERBITES_VIDEOS_DIR="videos"
export PORT=8000

# Create videos directory if it doesn't exist
mkdir -p $PAPERBITES_VIDEOS_DIR

# Install dependencies if needed
if [ ! -f ".dependencies_installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch .dependencies_installed
fi

# Make sure temp directory exists
mkdir -p temp_assets

# Run the API server
echo "Starting PaperBites API server on port $PORT..."
uvicorn api_server:app --host 0.0.0.0 --port $PORT --reload