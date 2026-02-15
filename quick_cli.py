# -*- coding: utf-8 -*-
"""
Quick CLI Launcher - Phase 5A
Launches interactive CLI with proper imports
"""

import sys
sys.path.insert(0, '.')

from lyra.cli.interactive_cli import InteractiveCLI

if __name__ == "__main__":
    cli = InteractiveCLI()
    cli.start()
