#!/usr/bin/env python3
"""
generate_cards.py - Runner for rendering profile README animated SVG cards.
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

if "--fetch" in sys.argv:
    fetch_script = os.path.join(HERE, "scripts", "fetch_contributions.py")
    if os.path.exists(fetch_script):
        subprocess.run([sys.executable, fetch_script])

render_script = os.path.join(HERE, "scripts", "render_readme_cards.py")
subprocess.run([sys.executable, render_script] + sys.argv[1:])
