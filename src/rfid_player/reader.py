"""RC522 reader wrapper (SPI0, CE0, RST on BCM25 / physical pin 22)."""
import time

RST_BCM = 25


class Reader:
    def __init__(self):
        import RPi.GPIO as GPIO  # provided by rpi-lgpio on Bookworm
        from mfrc522 import MFRC522

        self._gpio = GPIO
        self._rc = MFRC522(bus=0, device=0, pin_mode=GPIO.BCM, pin_rst=RST_BCM)
        self._MI_OK = self._rc.MI_OK
        self._PICC_REQIDL = self._rc.PICC_REQIDL

    def read_uid(self) -> str | None:
        """Return the UID of a card in the field as hex, or None."""
        status, _ = self._rc.MFRC522_Request(self._PICC_REQIDL)
        if status != self._MI_OK:
            return None
        status, uid = self._rc.MFRC522_Anticoll()
        if status != self._MI_OK:
            return None
        return "".join(f"{b:02X}" for b in uid[:4])

    def close(self) -> None:
        self._gpio.cleanup()


def wait_for_card(reader: Reader, poll: float = 0.15) -> str:
    while True:
        uid = reader.read_uid()
        if uid:
            return uid
        time.sleep(poll)
