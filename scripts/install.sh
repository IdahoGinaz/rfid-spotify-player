#!/usr/bin/env bash
# Run on the Pi from the repo root. Service files are rewritten for the current user and path.
set -euo pipefail

sudo apt update
sudo apt install -y python3-venv python3-dev git bluez curl swig liblgpio-dev

# Hardware: enable SPI, and the safe shutdown/wake button on GPIO3 (pin 5)
sudo raspi-config nonint do_spi 0
CONFIG=/boot/firmware/config.txt
grep -q '^dtoverlay=gpio-shutdown' $CONFIG || echo 'dtoverlay=gpio-shutdown' | sudo tee -a $CONFIG

python3 -m venv .venv
.venv/bin/pip install -e .
# mfrc522 pulls in the old RPi.GPIO; swap it for the rpi-lgpio shim
.venv/bin/pip uninstall -y RPi.GPIO
.venv/bin/pip install rpi-lgpio

[ -f /etc/rfid-player.env ] || sudo install -m 600 .env.example /etc/rfid-player.env
for f in rfid-player rfid-web; do
  sed -e "s|^User=.*|User=$USER|" -e "s|/home/jukebox/rfid-spotify-player|$PWD|" \
    systemd/$f.service | sudo tee /etc/systemd/system/$f.service >/dev/null
done
sudo systemctl daemon-reload

echo "Done. Follow docs/setup.md to install Spotify Soloist and pair it."
