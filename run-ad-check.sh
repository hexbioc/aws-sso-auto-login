#!/usr/bin/env bash

# Switch to project directory
cd "$(dirname $0)"

# Run the script while saving the logs of the current run
venv/bin/python main.py ad-check >>~/.cache/microsoft-ad-check.log 2>&1

tail -n500 ~/.cache/microsoft-ad-check.log >~/.cache/microsoft-ad-check.log.tmp
mv ~/.cache/microsoft-ad-check.log{.tmp,}
