# Wiring

## RC522 (SPI0)

| RC522 | Pi physical pin | Pi function |
|-------|-----------------|-------------|
| SDA (SS) | 24 | GPIO8 / CE0 |
| SCK | 23 | GPIO11 / SCLK |
| MOSI | 19 | GPIO10 / MOSI |
| MISO | 21 | GPIO9 / MISO |
| GND | 6 | Ground |
| RST | 22 | GPIO25 |
| 3.3V | 1 | 3.3V |
| IRQ | — | not connected |

**Power the RC522 from 3.3V only. 5V will damage it.** This matches your wiring.

## Power button

Momentary switch between **pin 5 (GPIO3/SCL)** and **pin 9 (GND)**.

- While running: a press triggers a clean shutdown (`dtoverlay=gpio-shutdown`, default GPIO3).
- While halted: a press wakes the Pi (GPIO3 is hard-wired for this by the firmware).
- After shutdown, wait for the green ACT LED to stop flashing before removing power.
- The Pi stays powered from USB (idle ~0.4 W), so the button acts as halt/wake rather than a true power cut.
- GPIO3 is the I2C SCL line, so don't enable I2C.
