#!/bin/bash

# Kill any existing process on port 3000 before starting
if command -v lsof &>/dev/null; then
  lsof -ti:3000 | xargs kill -9 2>/dev/null || true
else
  # Windows fallback via netstat + taskkill
  for pid in $(netstat -ano 2>/dev/null | grep ":3000 " | grep "LISTENING" | awk '{print $5}' | sort -u); do
    taskkill //PID "$pid" //F 2>/dev/null || true
  done
fi

cd frontend
npm install
npm start
