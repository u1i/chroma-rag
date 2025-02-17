#!/bin/bash
# Kill any running Flask app
lsof -i :5001 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null

# Activate venv and start app
source venv/bin/activate
python app.py
