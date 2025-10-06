export GOOGLE_API_KEY=<redacted>

uv run python -m uvicorn main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=localhost+2-key.pem --ssl-certfile=localhost+2.pem --reload