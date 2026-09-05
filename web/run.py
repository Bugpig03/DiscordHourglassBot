"""Application entry point for the Hourglass web interface."""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Retrieve host, port, and debug configuration with sensible defaults
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", 5002))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    app.run(debug=debug, host=host, port=port)