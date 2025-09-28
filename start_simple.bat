@echo off
echo Starting CrypTalk (Simple SQLite Version)...
echo.

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting CrypTalk Server...
python server.py

pause