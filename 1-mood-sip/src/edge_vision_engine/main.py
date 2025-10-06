# main.py

"""Thin entrypoint that creates the FastAPI app via factory and runs uvicorn.

Usage:
  python main.py             # uses env HOST/PORT/SSL_* if provided
  uvicorn main:app --reload  # uses uvicorn CLI
"""

import os
import uvicorn

from app.app_factory import create_app
from app.config import settings

app = create_app()


if __name__ == "__main__":
    keyfile = settings.ssl_keyfile
    certfile = settings.ssl_certfile

    if keyfile and certfile and os.path.exists(keyfile) and os.path.exists(certfile):
        print("🔒 SSL certificates found - starting HTTPS server on port", settings.port)
        uvicorn.run(app, host=settings.host, port=settings.port, ssl_keyfile=keyfile, ssl_certfile=certfile)
    else:
        print("⚠️  No SSL certificates configured - starting HTTP server on port", settings.port)
        uvicorn.run(app, host=settings.host, port=settings.port)
