#!/usr/bin/env bash

set -euo pipefail

VAR_FILE=$1
IMAGE_URL=$2
SCRIPT_PATH=${3:-../caasp-vmware.py}

IMAGE_NAME="$(basename "$IMAGE_URL")"
IMAGE_PATH="$(pwd)/$(basename "$IMAGE_URL")"

caasp_vmware() {
  python3 "$SCRIPT_PATH" --var-file "$VAR_FILE" "$@"
}

echo "INFO: Checking if we already have this image remotely: $IMAGE_NAME"

if ! caasp_vmware listimages | grep -q "$IMAGE_NAME"; then
    echo "INFO: Image does not exist remotely"

    echo "INFO: Checking if we need to download image locally: $IMAGE_PATH"
    if [[ ! -f "$IMAGE_PATH" ]]; then
        echo "INFO: Image does not exist locally, downloading..."
        echo "INFO: Downloading image: $IMAGE_URL"
        curl -sSL "$IMAGE_URL" -o "$IMAGE_PATH"
    else
        echo "INFO: Image found locally, skipping..."
    fi

    echo "INFO: Uploading image: $IMAGE_NAME"
    caasp_vmware pushimage --source-media "$IMAGE_PATH"
else
    echo "INFO: Image already exists..."
    echo "INFO: Skipping upload..."
fi

if [[ -f "$IMAGE_PATH" ]]; then
    echo "INFO: Cleaning local image"
    rm -vf "$IMAGE_PATH"
fi
