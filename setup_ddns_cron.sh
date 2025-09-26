#!/bin/bash

# This script checks for and adds a cron job for the Cloudflare DDNS script.

# --- Configuration ---
PYTHON_PATH=$(which python3) # Or specify the full path e.g., /usr/bin/python3
SCRIPT_PATH="/home/droid/upSignal/upSignal/cloudflare_ddns.py"
LOG_FILE="/tmp/ddns.log"
# --- End Configuration ---

# The full command to be added to cron
CRON_COMMAND="*/10 * * * * $PYTHON_PATH $SCRIPT_PATH >> $LOG_FILE 2>&1"

# Check if the cron job already exists
# The grep command uses -F to treat the string as fixed, and -q to be quiet.
crontab -l | grep -Fq "$CRON_COMMAND"

# $? is the exit status of the last command. 0 means grep found a match.
if [ $? -eq 0 ]; then
  echo "Cron job for DDNS script already exists. No changes made."
else
  echo "Cron job not found. Adding it now..."
  # Add the new cron job
  # The parenthesis create a subshell to combine the commands
  (crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -
  echo "Cron job added successfully."
fi
