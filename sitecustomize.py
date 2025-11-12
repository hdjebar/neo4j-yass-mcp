"""
sitecustomize.py - Auto-start coverage for subprocesses

This file is automatically imported by Python at startup.
It starts coverage measurement for subprocess testing.

Reference: https://coverage.readthedocs.io/en/latest/subprocess.html
"""

import os

# Only start coverage if COVERAGE_PROCESS_START is set
if "COVERAGE_PROCESS_START" in os.environ:
    try:
        import coverage

        coverage.process_startup()
    except ImportError:
        # coverage not installed, skip
        pass
