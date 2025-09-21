#!/bin/bash

echo "Script started at $(date)" >> /home/pi/cron_debug.log

cd /home/pi/heatingpi/heatingpi || exit 1

tmux new -d -s heatingpi '/home/pi/.local/bin/uv run main.py 2>&1 | tee -a output.txt'
