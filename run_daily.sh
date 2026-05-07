#!/bin/bash
cd /Users/parkjisu/Desktop/vibe_mail
source venv/bin/activate
python main.py >> logs/daily.log 2>&1
