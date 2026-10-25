# Setup guide

Requires a **Spotify Premium** account (needed once to create the Soloist API key).

## How it works

```
RFID card -> RC522 -> rfid-player (Python) --local WebSocket--> Spotify Soloist --> PipeWire --> Bluetooth speaker
```

[Spotify Soloist](https://developer.spotify.com/blog/2026-08-13-introducing-spotify-soloist) is Spotify's own
headless Spotify Connect client. `rfid-player` tells it to play a Spotify URI (track, album or playlist) over
its local WebSocket API, and audio goes out over Bluetooth.

> We first tried librespot/raspotify, but on some accounts it fails with `error audio key 0 1` and never plays.

## 1. Flash the SD card

1. Install Raspberry Pi Imager on your PC.
2. Choose **Raspberry Pi OS (other) > Raspberry Pi OS Lite (64-bit)**. Bookworm or the newer Trixie both work.
3. Click the settings/gear (Ctrl+Shift+X): set hostname `jukebox`, username `jukebox`, a password,
   Wi-Fi, locale, and **enable SSH**.
4. Write, insert the card, power the Pi, then `ssh jukebox@jukebox.local`.

## 2. Install the code

From your PC, copy the repo to the Pi (or `git clone` it there):

```powershell
scp -r rfid-spotify-player jukebox@jukebox.local:~/
```

On the Pi:

```bash
cd ~/rfid-spotify-player
chmod -R u+rwX .
find . -type f \( -name '*.sh' -o -name '*.py' -o -name '*.service' -o -name '*.toml' \) -exec sed -i 's/\r$//' {} +
chmod +x scripts/install.sh
./scripts/install.sh
sudo reboot
```

The script enables SPI, adds `dtoverlay=gpio-shutdown` (power button), and installs the Python package and
the card-reader and web services. Check the reader after the reboot:

```bash
ls /dev/spidev0.0
cd ~/rfid-spotify-player
.venv/bin/python -c "from rfid_player.reader import Reader, wait_for_card; r=Reader(); print('Tap a card...'); print('UID:', wait_for_card(r)); r.close()"
```

## 3. Bluetooth speaker

Install the audio stack and allow Bluetooth without a local login (needed on a headless Lite image,
otherwise `connect` fails with `br-connection-profile-unavailable` / "Protocol not available"):

```bash
sudo apt install -y pipewire-audio libspa-0.2-bluetooth wireplumber alsa-utils
sudo loginctl enable-linger $USER
systemctl --user enable --now pipewire pipewire-pulse wireplumber
mkdir -p ~/.config/wireplumber/wireplumber.conf.d
cat > ~/.config/wireplumber/wireplumber.conf.d/80-bluez-headless.conf <<'EOF'
wireplumber.profiles = {
  main = {
    monitor.bluez.seat-monitoring = disabled
  }
}
EOF
systemctl --user restart wireplumber
```

Put the speaker in pairing mode, then:

```bash
bluetoothctl
power on
agent on
default-agent
scan on            # wait for [NEW] Device <MAC> for your speaker
scan off
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
exit
```

`trust` makes it reconnect automatically on boot. Verify with `wpctl status` (speaker under **Sinks**, marked `*`)
and `speaker-test -t sine -f 440 -l 1`. If you restart `bluetooth` later, restart `wireplumber` afterwards too.

## 4. Install Spotify Soloist

1. In the [Spotify for Developers dashboard](https://developer.spotify.com/dashboard/soloist), generate a
   **Soloist API key** (Premium account). Keep it private.
2. On the Pi (`uname -m` should say `aarch64`; use the `arm32` build otherwise):

```bash
mkdir -p ~/.local/bin
bash ~/rfid-spotify-player/scripts/update-soloist.sh    # downloads the right build into ~/.local/bin
~/.local/bin/soloist --version
```

3. Store the key and install the user service:

```bash
install -m 600 /dev/null ~/.config/soloist.env
echo 'SOLOIST_API_KEY=<paste key here>' >> ~/.config/soloist.env
nano ~/.config/soloist.env          # check it
mkdir -p ~/.config/systemd/user
cp ~/rfid-spotify-player/systemd/soloist*.service ~/rfid-spotify-player/systemd/soloist-update.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now soloist
systemctl --user enable --now soloist-update.timer    # daily check for a newer build
systemctl --user status soloist --no-pager | head
```

4. **Pair once:** open Spotify on your phone (same Wi-Fi), pick **RFID Jukebox** from the device list and play
   something. It should come out of the speaker. This stores the login on the Pi.

Soloist builds expire (about 90 days). The daily timer installs a newer build automatically; see Maintenance.

## 5. Register cards (web page)

```bash
sudo nano /etc/rfid-player.env       # only PAUSE_ON_REMOVE is relevant here
sudo systemctl enable --now rfid-web
```

On any phone or laptop on the same Wi-Fi, open `http://jukebox.local` (or the Pi's IP address).
Tap a new card on the jukebox and the page shows "New card detected". Paste a Spotify share link
(Share > Copy link), the name fills in automatically, then press **Save card**. The page also lists
saved cards, and lets you change or remove them. Changes work immediately, with no restart.
There's no password, so anyone on your home Wi-Fi can use it.

Command-line alternative: `.venv/bin/rfid-player add`. Mappings are in `~/.config/rfid-player/cards.json`.

## 6. Run on boot

```bash
sudo systemctl enable --now rfid-player
journalctl -u rfid-player -f
```

## Maintenance

| Task | How often | What to do |
|---|---|---|
| Soloist updates | Automatic, daily 04:00 | Builds expire after about 90 days; the `soloist-update.timer` installs a newer build and restarts Soloist (only if it changed). Check with `systemctl --user list-timers soloist-update.timer` and `~/.local/bin/soloist --version`. If it ever exits with code `10`, run `bash ~/rfid-spotify-player/scripts/update-soloist.sh` by hand. |
| Back up the cards | After adding cards | On your PC: `.\scripts\backup-cards.ps1` saves `cards.json` to `OneDrive\Backups\jukebox`. To restore, `scp` it back to `~/.config/rfid-player/cards.json`. |
| Back up the SD card | Once it is working, then after big changes | Shut the Pi down with the button and put the card in your PC. Use Win32 Disk Imager (Read) to save an `.img` to a local drive, compress it (7-Zip), then copy the archive to OneDrive. The image is as big as the card (16 GB), so check your OneDrive space. |
| Rotate the Soloist API key | If it leaks | Generate a new key in the Spotify dashboard, edit `~/.config/soloist.env`, then `systemctl --user restart soloist`. As far as I can tell Spotify offers no API for this, so it can't be automated. I found no sign that keys expire. |
| OS updates | Occasionally | `sudo apt update && sudo apt full-upgrade`, then reboot. After a Bluetooth service restart, also restart WirePlumber. |

### Moving an existing install to automatic Soloist updates

If Soloist is already installed in `/usr/local/bin` (the older instructions), run once on the Pi:

```bash
cd ~/rfid-spotify-player
mkdir -p ~/.local/bin ~/.config/systemd/user
bash scripts/update-soloist.sh
cp systemd/soloist.service systemd/soloist-update.service systemd/soloist-update.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart soloist
systemctl --user enable --now soloist-update.timer
systemctl --user status soloist --no-pager | head -5
```

## Troubleshooting

| Symptom | Check |
|---|---|
| No card reads | `ls /dev/spidev0.0` exists? Re-check wiring; 3.3V only. |
| "Playback failed" / connection refused | `systemctl --user status soloist`; it must run with `--ws 127.0.0.1:9090`. |
| "command requires authentication" | Pair once from the Spotify app (step 4). |
| Device not in Spotify app | Phone and Pi on the same network; no client isolation on the router. |
| No sound | `bluetoothctl info <MAC>` shows Connected; `wpctl status`; `speaker-test`. |
| Button does nothing | `grep gpio-shutdown /boot/firmware/config.txt`; reboot after adding. |
