#!/bin/bash
set -e

# Use PORT from environment, default to 8080 if not set
PORT=${PORT:-8080}

echo "Starting uvicorn on port $PORT"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"