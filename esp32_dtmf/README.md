# ESP32 DTMF Tone Generator

Generates standard ITU-T DTMF dual-tone signals using ESP32's DAC output
and a piezo buzzer. Type digits from your laptop keyboard via Serial Monitor.

## Connections

| ESP32 Pin | Component |
|-----------|-----------|
| GPIO25 (DAC1) | 100Ω resistor → Buzzer (+) |
| GND | Buzzer (−) |
| USB | Laptop |

## Usage

1. Upload `esp32_dtmf.ino` via Arduino IDE (Board: ESP32 Dev Module)
2. Open Serial Monitor at 115200 baud
3. Type 0-9, *, #, or A-D and press Enter
4. Buzzer plays the DTMF tone; Serial Monitor shows frequency info

## DTMF Standard

Each key produces two simultaneous sinusoidal tones:
- Row frequencies: 697, 770, 852, 941 Hz
- Column frequencies: 1209, 1336, 1477, 1633 Hz
