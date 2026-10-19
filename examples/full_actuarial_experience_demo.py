"""
Full Actuarial Reinsurance Experience Demo
==========================================

Demonstrates:
1. Longitudinal portfolio generation & exposure tracking
2. SOA 2015 VBT benchmark attachment
3. Multi-dimensional A/E experience study with Garwood Poisson CIs
4. Limited Fluctuation & Bühlmann-Straub credibility
5. Actuarial GLM with log-exposure offset
6. Non-Life treaty layering & heavy-tail simulation
7. Solvency II 1-in-200 year SCR capital relief
"""

import sys
import os

# Ensure package is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reinsurance_analytics.cli import run_full_analysis

if __name__ == "__main__":
    run_full_analysis(output_dir="output", policies=10000, trials=5000)
