"""PyInstaller entry point.

Import ``app.main`` as a package module so relative imports inside ``app/`` work
when frozen. Do not point PyInstaller at ``app/main.py`` directly.
"""
from app.main import main

if __name__ == "__main__":
    main()
