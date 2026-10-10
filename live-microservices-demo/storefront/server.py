"""
Storefront Web Server (Port 9100)
Serves the customer-facing e-commerce storefront web application.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PORT = int(os.getenv("PORT", 9100))
app = FastAPI(title="Synapse Hardware Hub Storefront", version="1.0.0")

static_dir = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
@app.get("/index.html")
async def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(static_dir, "app.js"))


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "storefront", "port": PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
