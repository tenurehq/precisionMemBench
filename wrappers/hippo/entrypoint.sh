#!/bin/sh
# Each start serves a new, empty store, with one admin key for the wrapper so /reset can delete rows.
set -e
rm -rf /data/store /data/key.json
mkdir -p /data/store
cd /data/store
hippo init --no-hooks --no-schedule --no-learn --no-embeddings
hippo auth create --role admin --label precisionmembench --json > /data/key.json
exec hippo serve --port 6789
