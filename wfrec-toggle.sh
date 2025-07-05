#!/bin/bash

PIDFILE=/tmp/wfrec.pid

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Stopping recording..."
    kill "$(cat "$PIDFILE")"
    rm "$PIDFILE"
else
    echo "Starting recording..."
    wf-recorder -f "$HOME/Videos/recording_$(date +%Y%m%d_%H%M%S).mp4" &
    echo $! > "$PIDFILE"
fi
