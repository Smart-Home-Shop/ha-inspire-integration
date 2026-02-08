#!/usr/bin/env bash
# Restart the Home Assistant container to pick up integration/code changes.
set -e
cd "$(dirname "$0")"

docker compose restart homeassistant
echo "Home Assistant is restarting..."
