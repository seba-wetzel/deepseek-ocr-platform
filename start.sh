#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

trap cleanup SIGINT

echo "Starting DeepSeek OCR Platform..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run set up commands first."
    exit 1
fi

# Start Backend
echo "Starting Backend..."
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend running on PID $BACKEND_PID"

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend running on PID $FRONTEND_PID"

echo "Platform is running!"
echo "Frontend: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop."

wait
