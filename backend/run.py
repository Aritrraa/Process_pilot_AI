"""
ProcessPilot AI — Enterprise Knowledge & Operations Copilot
Run with: python run.py
"""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    is_prod = os.getenv("DATABASE_URL") is not None
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=not is_prod
    )
