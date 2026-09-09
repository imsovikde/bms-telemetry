#!/usr/bin/env python3
"""
Standalone 100-Cycle Deep Verification & Stress Test Harness for BMS Telemetry
"""
import sys
import os

# Add local path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bms_engine

if __name__ == "__main__":
    bms_engine.run_100_cycle_verification()
