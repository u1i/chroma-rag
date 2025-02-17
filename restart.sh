#!/bin/bash

# Kill any running Flask app
pkill -f "python app.py" || true

# Kill any process using port 8080
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true

# Wait a moment for the port to be freed
sleep 1

# Start the app
python app.py
