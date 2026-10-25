"""Card UID -> Spotify URI mapping stored in a JSON file."""
import json
import time
from pathlib import Path


class CardMap:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.cards: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.cards = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, uid: str) -> dict | None:
        self.load()  # pick up edits without restarting the service
        return self.cards.get(uid)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cards, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic, so the player never reads a half-written file

    def add(self, uid: str, uri: str, name: str = "") -> None:
        self.load()
        self.cards[uid] = {"uri": uri, "name": name}
        self._save()

    def remove(self, uid: str) -> None:
        self.load()
        self.cards.pop(uid, None)
        self._save()


def record_scan(path: Path, uid: str) -> None:
    """Remember the most recent card so the web UI can offer to register it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"uid": uid, "time": time.time()}), encoding="utf-8")


def last_scan(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def normalize_uri(value: str) -> str:
    """Accept spotify:track:ID URIs or open.spotify.com URLs; return a URI."""
    value = value.strip()
    if value.startswith("spotify:"):
        return value
    if "open.spotify.com/" in value:
        parts = value.split("open.spotify.com/")[1].split("?")[0].split("/")
        parts = [p for p in parts if not p.startswith("intl-")]
        if len(parts) >= 2:
            return f"spotify:{parts[0]}:{parts[1]}"
    raise ValueError(f"Not a Spotify URI or URL: {value}")
