#!/usr/bin/env python3
"""Run the current location-picker browser regression suite (mocked services)."""
import asyncio
from location_browser_test import run
if __name__ == '__main__': asyncio.run(run())
