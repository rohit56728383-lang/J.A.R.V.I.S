# J.A.R.V.I.S MARK 2090 (web) - no API keys

Browser = eyes/ears/mouth (camera, MediaPipe hand tracking, Web Speech). Python server = brain (FastAPI).
Render has no camera or mic, so those run in YOUR browser; the server only answers /api/ask.

## Run locally
    uv venv --python 3.13 && uv pip install -r requirements.txt
    uv run uvicorn main:app --reload      # open http://localhost:8000 in Chrome/Edge

## Deploy on Render
1. Push this folder to a GitHub repo.
2. Render dashboard -> New -> Blueprint -> pick the repo (it reads render.yaml). Deploy.
3. Open the https URL in Chrome/Edge. Camera/mic require https (Render provides it).
Free plan sleeps when idle; the first request after a sleep takes ~30-60s.
