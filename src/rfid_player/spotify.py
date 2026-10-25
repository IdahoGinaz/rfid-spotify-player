"""Control a local Spotify Soloist daemon over its WebSocket API."""
import json
import os

import websocket  # websocket-client

WS_URL = os.environ.get("SOLOIST_WS", "ws://127.0.0.1:9090")
TIMEOUT = 5


class Player:
    def _send(self, command: dict) -> None:
        ws = websocket.create_connection(WS_URL, timeout=TIMEOUT)
        try:
            ws.send(json.dumps({"type": "command", **command}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("type") == "command_result":
                    return
                if msg.get("type") == "error":
                    raise RuntimeError(msg.get("message", "Soloist error"))
        finally:
            ws.close()

    def state(self) -> dict:
        ws = websocket.create_connection(WS_URL, timeout=TIMEOUT)
        try:
            ws.send(json.dumps({"type": "command", "command": "get_state"}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("type") == "playback_state":
                    return msg
                if msg.get("type") == "error":
                    raise RuntimeError(msg.get("message", "Soloist error"))
        finally:
            ws.close()

    def is_loaded(self, uri: str) -> bool:
        """True if the track or playlist/album currently loaded in Soloist is `uri`."""
        st = self.state()
        return uri in ((st.get("item") or {}).get("uri"), (st.get("context") or {}).get("uri"))

    def play(self, uri: str | None = None) -> None:
        """Start a URI, or resume the current item when no URI is given."""
        self._send({"command": "play", **({"uri": uri} if uri else {})})

    def pause(self) -> None:
        try:
            self._send({"command": "pause"})
        except Exception:
            pass
