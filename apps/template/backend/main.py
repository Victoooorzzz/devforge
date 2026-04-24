# apps/template/backend/main.py
import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from backend_core import create_app

app = create_app(
    title="DevForge Template",
    description="Template product backend",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
