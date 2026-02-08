#!/usr/bin/env bash
# Run Home Assistant via docker-compose with this repo's config and Inspire custom component.
set -e
cd "$(dirname "$0")"

CONFIG_DIR="config"
if [[ ! -d "$CONFIG_DIR" ]]; then
  mkdir -p "$CONFIG_DIR"
fi
if [[ ! -f "$CONFIG_DIR/configuration.yaml" ]]; then
  echo "default_config:" > "$CONFIG_DIR/configuration.yaml"
fi

docker compose up
