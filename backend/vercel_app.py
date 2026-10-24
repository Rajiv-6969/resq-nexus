"""Vercel entrypoint: serves the ResQ Nexus API under /api on the site's own domain.

Vercel passes the full request path (for example /api/scenarios) to the backend
service, so the API from main.py is mounted under /api here. Local development
keeps using main:app, where the same routes live at the root.
"""
from fastapi import FastAPI

from main import app as api

app = FastAPI(title="ResQ Nexus", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)
