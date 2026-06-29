# app.py - Compatibility wrapper forwarding execution to the new clean architecture entry point (main.py)
import logging
from main import app, fastapi_app, gradio_ui

logger = logging.getLogger("talentree.compatibility")
logger.info("Compatibility wrapper active: Redirecting app.py to main.py")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
