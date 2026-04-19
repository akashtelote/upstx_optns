import os

# Timeouts for API connections
CONNECTION_TIMEOUT = float(os.getenv("CONNECTION_TIMEOUT", "10.0"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "30.0"))
