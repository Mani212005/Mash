"""
Mash Voice Platform - Entry Point

Run the voice agent platform server.
"""

import uvicorn

from app.config import get_settings


def main():
    """Run the Mash Voice Platform server."""
    settings = get_settings()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🎙️  Mash Voice Platform v0.1.0                              ║
║                                                               ║
║   Starting server at http://{settings.host}:{settings.port}            ║
║   API Documentation: http://{settings.host}:{settings.port}/docs       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
