"""Main loop: scan card -> play mapped Spotify URI."""
import argparse
import logging
import os
import time
from pathlib import Path

from .cards import CardMap, normalize_uri, record_scan
from .reader import Reader, wait_for_card

CARDS_FILE = Path(os.environ.get("CARDS_FILE", Path.home() / ".config/rfid-player/cards.json"))
LAST_SCAN_FILE = Path(os.environ.get("LAST_SCAN_FILE", Path.home() / ".config/rfid-player/last_scan.json"))
PAUSE_ON_REMOVE = os.environ.get("PAUSE_ON_REMOVE", "1") == "1"
REMOVE_GRACE = 1.0  # seconds without a read before a card counts as removed

log = logging.getLogger("rfid_player")


def run() -> None:
    from .spotify import Player

    cards, reader, player = CardMap(CARDS_FILE), Reader(), Player()
    current, last_seen = None, 0.0
    paused_uid = None  # card whose music we paused when it was lifted
    log.info("Ready. Waiting for cards...")
    try:
        while True:
            uid = reader.read_uid()
            now = time.monotonic()
            if uid:
                last_seen = now
                if uid != current:
                    current = uid
                    record_scan(LAST_SCAN_FILE, uid)
                    entry = cards.get(uid)
                    if entry is None:
                        log.warning("Unknown card %s (run rfid-player add)", uid)
                    else:
                        try:
                            # Only resume if this card's music is still what Soloist has loaded
                            resume = uid == paused_uid and player.is_loaded(entry["uri"])
                            log.info("Card %s -> %s%s", uid, entry.get("name") or entry["uri"],
                                     " (resume)" if resume else "")
                            player.play(None if resume else entry["uri"])
                            paused_uid = None
                        except Exception:
                            log.exception("Playback failed")
            elif current and now - last_seen > REMOVE_GRACE:
                if PAUSE_ON_REMOVE and cards.get(current):
                    player.pause()
                    paused_uid = current
                current = None
            time.sleep(0.15)
    finally:
        reader.close()


def add() -> None:
    cards = CardMap(CARDS_FILE)
    reader = Reader()
    try:
        print("Hold a card to the reader...")
        uid = wait_for_card(reader)
        print(f"Card UID: {uid}")
        uri = normalize_uri(input("Spotify URI or share URL: "))
        name = input("Label (optional): ").strip()
        cards.add(uid, uri, name)
        print(f"Saved to {CARDS_FILE}")
    finally:
        reader.close()


def main() -> None:
    p = argparse.ArgumentParser(prog="rfid-player")
    p.add_argument("command", choices=["run", "add", "web"], nargs="?", default="run")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cmd = p.parse_args().command
    if cmd == "web":
        from .web import serve
        serve()
        return
    {"run": run, "add": add}[cmd]()


if __name__ == "__main__":
    main()
