#!/bin/bash
# Install Playwright browsers if not present
export PLAYWRIGHT_BROWSERS_PATH=/pw-browsers

# Check if the expected browser exists
if [ ! -f "/pw-browsers/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell" ] && \
   [ ! -f "/pw-browsers/chromium_headless_shell-1208/chrome-linux/headless_shell" ]; then
    echo "Installing Playwright browsers..."
    playwright install chromium
    echo "Playwright browsers installed"
else
    echo "Playwright browsers already installed"
fi
