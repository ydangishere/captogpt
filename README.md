# Live Caption Enter Toggle

Capture Windows Live Captions and send to GPT in real-time while capture is ON.

## What this project does

- Press `Enter` once: start collecting captions and send updates to GPT immediately.
- Press `Enter` again: stop sending.
- Press `Ctrl + C`: exit.

This matches your flow: Enter toggles ON/OFF, and ON mode sends continuously.

## Requirements

- Windows 11 (Live Captions available)
- Python 3.10+
- OpenAI API key

## Setup (PowerShell)

Run these commands in the project folder:

```powershell
cd "D:\captogpt-enter"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_openai_api_key_here"
```

Purpose:

- `python -m venv .venv`: create isolated Python environment.
- `Activate.ps1`: activate that environment for this terminal.
- `pip install -r requirements.txt`: install all required packages.
- `OPENAI_API_KEY`: allow the app to call GPT.

## Run (PowerShell)

```powershell
cd "D:\captogpt-enter"
.\.venv\Scripts\Activate.ps1
python .\live_caption_enter_toggle.py
```

Purpose:

- Start the module and listen for global Enter key toggles.

## Quick run option

You can also double-click `start.bat`.

Purpose:

- Auto-create venv (if missing), install dependencies, and start the app.

## Usage

1. Open Live Captions with `Ctrl + Win + L`.
2. In the running terminal, press `Enter` to start capture.
3. Speak/play audio in Chrome (or any app).
4. While ON, each new caption update is sent to GPT.
5. Press `Enter` again to stop sending.
6. Read GPT output in terminal.

## Notes

- Live Captions is system-level, not Chrome-only.
- If no captions appear, make sure Live Captions is open and receiving audio.
