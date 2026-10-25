# RFID Spotify Player

Tap an RFID card on a Raspberry Pi 3 + RC522 reader and a Spotify track, album or playlist plays on a Bluetooth speaker.
A momentary button provides safe shutdown and wake.

- [Wiring](docs/wiring.md)
- [Setup guide](docs/setup.md), from flashing the SD card to running on boot

## Using the jukebox

**Play music:** place a card on the reader. Its Spotify track, album or playlist starts on the speaker.

**Pause and resume:** lift the card to pause. Put the same card back to carry on where it stopped.
If someone played something else from a phone in the meantime, the card starts its own music again from the beginning.

**Change music:** put a different card on the reader.

**Add or change a card:**
1. On a phone or laptop on the home Wi-Fi, open `http://jukebox.local`.
2. Place the new card on the reader. The page shows "New card detected".
3. In Spotify, choose Share > Copy link for a track, album or playlist, and paste it into the page.
4. Check the name and press **Save card**. Tap the card to try it.

Saved cards can be changed or removed from the same page.

**Power:** press the button once to shut down. Wait for the green light on the Pi to stop flashing, then it is safe to
unplug. Press the button again to start it up. The speaker should be switched on first.

**If nothing plays:** check the speaker is on and connected, then press the button to shut down and start again.
See the troubleshooting table in the [setup guide](docs/setup.md).

## Layout

```
src/rfid_player/   reader (RC522), cards (UID->URI map), spotify (Soloist WebSocket client), web, main
scripts/install.sh one-shot Pi install (SPI, shutdown button, Python package, services)
systemd/           rfid-player, rfid-web (system) and soloist (user) service units
```

## Usage

```
rfid-player add    # register a card to a Spotify link
rfid-player run    # main loop (used by the systemd service)
rfid-player web    # card manager web page at http://jukebox.local
```

Playback uses [Spotify Soloist](https://developer.spotify.com/blog/2026-08-13-introducing-spotify-soloist).
A Premium account is needed once to create its API key.
