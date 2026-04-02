#!/usr/bin/env bash

# Switch to project directory
cd "$(dirname $0)"

# Run the script while saving the logs of the current run
venv/bin/python main.py >>~/.cache/aws-sso-auto-login.log 2>&1

tail -n500 ~/.cache/aws-sso-auto-login.log >~/.cache/aws-sso-auto-login.log.tmp
mv ~/.cache/aws-sso-auto-login.log{.tmp,}
