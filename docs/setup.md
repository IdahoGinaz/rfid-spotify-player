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

On the Pi, clone the repo (this also makes updates a simple `git pull`):

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git
git clone https://github.com/IdahoGinaz/rfid-spotify-player.git
cd rfid-spotify-player
chmod +x scripts/*.sh
./scripts/install.sh
sudo reboot
```

The script enables SPI, adds `dtoverlay=gpio-shutdown` (power button), installs the Python package, and
installs and **enables** the card-reader and web services. Check the reader after the reboot (stop the
service first, since only one program can use the reader):

```bash
ls /dev/spidev0.0
cd ~/rfid-spotify-player
sudo systemctl stop rfid-player
.venv/bin/python -c "from rfid_player.reader import Reader, wait_for_card; r=Reader(); print('Tap a card...'); print('UID:', wait_for_card(r)); r.close()"
sudo systemctl start rfid-player
```

If you scp'd the code from Windows instead of cloning, run
`chmod -R u+rwX . && find . -type f \( -name '*.sh' -o -name '*.py' -o -name '*.service' -o -name '*.toml' \) -exec sed -i 's/\r$//' {} +` first.

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

The web page runs as the `rfid-web` service (started by `install.sh`). `sudo nano /etc/rfid-player.env` holds
the settings; only `PAUSE_ON_REMOVE` matters here.

On any phone or laptop on the same Wi-Fi, open `http://jukebox.local` (or the Pi's IP address).
Tap a new card on the jukebox and the page shows "New card detected". Paste a Spotify share link
(Share > Copy link), the name fills in automatically, then press **Save card**. The page also lists
saved cards, and lets you change or remove them. Changes work immediately, with no restart.
There's no password, so anyone on your home Wi-Fi can use it.

Command-line alternative: `.venv/bin/rfid-player add`. Mappings are in `~/.config/rfid-player/cards.json`.

## 6. Run on boot

`install.sh` enables `rfid-player` and `rfid-web`, so they start at boot. Watch the log with:

```bash
journalctl -u rfid-player -f
```

Both services set `WorkingDirectory` to the repo, because the `lgpio` library writes a small temporary file to
the current directory and crashes if it can't. `soloist.service` waits for the network before starting, because
Soloist logs in once at start-up and doesn't retry (`login failed: make sure --api-key is valid` right after a
boot means it started before Wi-Fi was up; `systemctl --user restart soloist` fixes it).

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

### Updating the Pi

```bash
cd ~/rfid-spotify-player && git pull
```

If a unit file changed, copy it into place and reload: system units to `/etc/systemd/system/` (then
`sudo systemctl daemon-reload && sudo systemctl restart rfid-player rfid-web`), Soloist units to
`~/.config/systemd/user/` (then `systemctl --user daemon-reload && systemctl --user restart soloist`).
`install.sh` is safe to re-run; it rewrites the system units.

## Rebuild from scratch

Use this if the SD card is corrupt or the Pi won't come up on Wi-Fi (the Pi 3's micro-USB port is power only, so
there's no way to log in over it).

1. **Save what you can first.** If the card still reads, copy `cards.json` off it. You can also restore from
   `OneDrive\Backups\jukebox` (see `backup-cards.ps1`), or restore the whole SD image.
2. **Reflash** (section 1). Use the same hostname and username (`jukebox`) and re-enter the Wi-Fi.
3. **Clear the old SSH host key** on your PC, or SSH refuses with "REMOTE HOST IDENTIFICATION HAS CHANGED":
   `ssh-keygen -R jukebox.local`, then `ssh jukebox@jukebox.local`.
4. **Install the code** (section 2). `install.sh` also fixes the `rpi-lgpio` shim.
5. **Bluetooth** (section 3): the WirePlumber headless file and `loginctl enable-linger`, then pair and trust the speaker.
   `Failed to set power on` usually means rfkill: `sudo rfkill unblock bluetooth`.
6. **Soloist** (section 4): generate a **new** API key (don't paste it anywhere public), then pair once from the phone.
7. **Cards**: open `http://jukebox.local` and re-add them, or `scp cards.json jukebox@jukebox.local:~/.config/rfid-player/cards.json`.
8. **Test a cold boot**: `sudo reboot`, wait two minutes, tap a card. Then take a fresh SD image.

Always shut down with the button (or `sudo shutdown -h now`) and wait for the green light to stop before pulling power.

## Troubleshooting

| Symptom | Check |
|---|---|
| No card reads | `ls /dev/spidev0.0` exists? Re-check wiring; 3.3V only. |
| `No module named 'RPi'` | The `rpi-lgpio` shim is missing: `.venv/bin/pip install --force-reinstall --no-deps rpi-lgpio`. |
| `rfid-player` or `rfid-web` is `inactive` or keeps restarting | `systemctl is-enabled rfid-player rfid-web` (enable with `sudo systemctl enable --now ...`); `journalctl -u rfid-player -n 20`. `FileNotFoundError: .lgd-nfy-3` means the unit lacks `WorkingDirectory`. |
| Web page won't load | It's on port 80: `http://jukebox.local`, no port. Some phones can't resolve `.local`; use the Pi's IP (`hostname -I`). |
| "Playback failed" / connection refused | `systemctl --user status soloist`; it must run with `--ws 127.0.0.1:9090`. |
| "command requires authentication" | Soloist isn't logged in. Check its log for `login failed`; restart it once Wi-Fi is up, or pair from the Spotify app (step 4). |
| Device not in Spotify app | Phone and Pi on the same network; no client isolation on the router. |
| No sound | `bluetoothctl info <MAC>` shows Connected; `wpctl status`; `speaker-test`. |
| Button does nothing | `grep gpio-shutdown /boot/firmware/config.txt`; reboot after adding. |
