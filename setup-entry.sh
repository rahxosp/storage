#!/bin/bash
# ESRGAN Server Setup - Entry Point
# This script downloads and prepares the main setup script

echo "======================================"
echo "ESRGAN Server Setup - Entry Point"
echo "======================================"

MAIN_SCRIPT_URL="https://raw.githubusercontent.com/rahxosp/storage/refs/heads/main/esrgan-setup-main.sh"
SCRIPT_NAME="esrgan-setup-main.sh"

echo "Downloading main setup script..."
wget -O "$SCRIPT_NAME" "$MAIN_SCRIPT_URL" || curl -o "$SCRIPT_NAME" "$MAIN_SCRIPT_URL"

if [ ! -f "$SCRIPT_NAME" ]; then
    echo "Error: Failed to download main script"
    exit 1
fi

echo "Setting permissions..."
chmod 777 "$SCRIPT_NAME"

echo ""
echo "======================================"
echo "Setup script ready!"
echo "Run: ./$SCRIPT_NAME"
echo "======================================"
