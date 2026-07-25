"""
Day 38 -- Shared app-level state (start time, version), kept separate from main.py
to avoid a circular import between main.py and the routers that need it (health.py).
"""

import time

APP_START_TIME = time.time()
API_VERSION = "1.0.0"
