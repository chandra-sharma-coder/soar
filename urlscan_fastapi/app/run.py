"""
Application Runner
Development server launcher for the URLscan.io FastAPI application
"""
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def start_server():
    """Start the development server with hot-reload enabled."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    print("=" * 60)
    print("URLscan.io SOAR SDK - FastAPI Server")
    print("=" * 60)
    print("Starting server at http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Alternative Docs: http://localhost:8000/redoc")
    print("=" * 60)
    start_server()