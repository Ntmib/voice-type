#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
VOICETYPE_TOKEN=***REMOVED*** python3 voice_type.py
