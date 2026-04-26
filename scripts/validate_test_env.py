"""Validate that required test environment dependencies are available."""
import sys


REQUIRED = ["black", "flake8", "pytest", "aiohttp", "yaml", "voluptuous"]

missing = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print(f"ERROR: Missing packages: {', '.join(missing)}", file=sys.stderr)
    print("Run: pip install -r requirements_test.txt", file=sys.stderr)
    sys.exit(1)

print(f"Test environment OK (Python {sys.version.split()[0]})")
