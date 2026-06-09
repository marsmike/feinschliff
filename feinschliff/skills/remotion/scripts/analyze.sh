#!/usr/bin/env bash
# Thin wrapper for video_to_storyboard.py
exec python3 "$(dirname "$0")/video_to_storyboard.py" "$@"
