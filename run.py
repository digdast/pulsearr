import uvicorn
import sys
from pulsearr.config import config

def main():
    print(r"""
  ____  _   _ _     ____  _____    _    ____  ____  
 |  _ \| | | | |   / ___|| ____|  / \  |  _ \|  _ \ 
 | |_) | | | | |   \___ \|  _|   / _ \ | |_) | |_) |
 |  __/| |_| | |___ ___) | |___ / ___ \|  _ <|  _ < 
 |_|    \___/|_____|____/|_____/_/   \_\_| \_\_| \_\\
 
 >> Next-Gen Ultra-Fast Asynchronous Python TV PVR <<
 >> Better, lighter, and faster than Sonarr.       <<
    """)
    print(f" * Web UI Dashboard : http://localhost:{config.port}")
    print(f" * OpenAPI Swagger  : http://localhost:{config.port}/docs")
    print(f" * Root Media Path  : {config.root_folder}")
    print(f" * Async Database   : SQLite (WAL Mode active)\n")

    uvicorn.run(
        "pulsearr.main:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
