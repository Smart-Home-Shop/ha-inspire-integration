#!/usr/bin/env bash
# Run Home Assistant in Docker with this repo's config and Inspire custom component.
set -e
cd "$(dirname "$0")"

CONFIG_DIR="config"
if [[ ! -d "$CONFIG_DIR" ]]; then
  mkdir -p "$CONFIG_DIR"
fi
if [[ ! -f "$CONFIG_DIR/configuration.yaml" ]]; then
  echo "default_config:" > "$CONFIG_DIR/configuration.yaml"
fi

docker run --rm -it \
  --name inspire-ha \
  -p 8123:8123 \
  -v "$(pwd)/$CONFIG_DIR:/config" \
  -v "$(pwd)/custom_components/inspire:/config/custom_components/inspire" \
  ghcr.io/home-assistant/home-assistant:stable
