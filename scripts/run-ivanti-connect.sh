#!/usr/bin/env bash

# Switch to project directory
cd "$(dirname $0)/../"

# Run the script while saving the logs of the current run
venv/bin/python main.py ivanti-connect >>~/.cache/auto-ivanti-connect.log 2>&1

if [ $? -ne 0 ]; then
    printf 'Failed to generate DSID cookie\n'
    exit 1
fi

ivanti_host=$(cat .env | grep 'IVANTI_HOST=' | cut -d'=' -f2 | tr -d "'\"\n")
cookie=$(cat /tmp/.ivanti-cookie | tr -d "\n")

# Delete the cookie file to limit leakage
rm /tmp/.ivanti-cookie

sudo openconnect --protocol nc -C "$cookie" "$ivanti_host"

tail -n500 ~/.cache/auto-ivanti-connect.log >~/.cache/auto-ivanti-connect.log.tmp
mv ~/.cache/auto-ivanti-connect.log{.tmp,}
