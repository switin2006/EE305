/*
 * ESP32 DTMF Tone Generator
 * 
 * Receives digit keypress via Serial (USB), generates dual-tone DTMF
 * signal on DAC output (GPIO25) driving a piezo buzzer, and prints
 * the frequency pair to Serial Monitor as proof.
 *
 * Board: ESP32 Dev Module (Robocraze 30-pin)
 * DAC Output: GPIO25 (DAC1)
 * Buzzer: Piezo buzzer between GPIO25 and GND
 */

#include <math.h>

// ── DAC Config ──
#define DAC_PIN       25        // ESP32 DAC1 (GPIO25)
#define SAMPLE_RATE   32000     // Hz — Nyquist OK for max DTMF freq 1633 Hz
#define TONE_DURATION 300       // ms per tone burst
#define DAC_AMPLITUDE 120       // 0-127 range (half of 0-255), keeps sum in range

// ── DTMF Frequency Table ──
// Standard ITU-T DTMF: each key = low freq + high freq
// Rows: 697, 770, 852, 941 Hz
// Cols: 1209, 1336, 1477, 1633 Hz

struct DTMFTone {
  char key;
  uint16_t freqLow;
  uint16_t freqHigh;
};

const DTMFTone dtmfTable[] = {
  {'1',  697, 1209},
  {'2',  697, 1336},
  {'3',  697, 1477},
  {'A',  697, 1633},
  {'4',  770, 1209},
  {'5',  770, 1336},
  {'6',  770, 1477},
  {'B',  770, 1633},
  {'7',  852, 1209},
  {'8',  852, 1336},
  {'9',  852, 1477},
  {'C',  852, 1633},
  {'*',  941, 1209},
  {'0',  941, 1336},
  {'#',  941, 1477},
  {'D',  941, 1633}
};

const int NUM_KEYS = sizeof(dtmfTable) / sizeof(dtmfTable[0]);

// ── Find DTMF entry for a character ──
int findKey(char c) {
  // Accept lowercase a-d as A-D
  if (c >= 'a' && c <= 'd') c = c - 32;
  for (int i = 0; i < NUM_KEYS; i++) {
    if (dtmfTable[i].key == c) return i;
  }
  return -1;
}

// ── Play dual-tone DTMF on DAC ──
void playDTMF(uint16_t f1, uint16_t f2, uint16_t durationMs) {
  uint32_t totalSamples = (uint32_t)SAMPLE_RATE * durationMs / 1000;
  float omega1 = 2.0f * PI * f1 / SAMPLE_RATE;
  float omega2 = 2.0f * PI * f2 / SAMPLE_RATE;
  uint32_t delayUs = 1000000UL / SAMPLE_RATE;

  for (uint32_t n = 0; n < totalSamples; n++) {
    // Sum two sinusoids, scale to DAC range [0, 255]
    float sample = sinf(omega1 * n) + sinf(omega2 * n);
    // sample is in [-2, +2], map to [0, 255]
    uint8_t dacVal = (uint8_t)(128 + (int)(sample * DAC_AMPLITUDE / 2.0f));
    dacWrite(DAC_PIN, dacVal);
    delayMicroseconds(delayUs);
  }

  // Silence after tone
  dacWrite(DAC_PIN, 128);
}

// ── Musical note name for a frequency (nearest) ──
const char* noteName(uint16_t freq) {
  // DTMF frequencies and their nearest musical notes
  switch (freq) {
    case 697:  return "F5 (closest)";
    case 770:  return "G5 (closest)";
    case 852:  return "Ab5 (closest)";
    case 941:  return "Bb5 (closest)";
    case 1209: return "D6 (closest)";
    case 1336: return "E6 (closest)";
    case 1477: return "F#6 (closest)";
    case 1633: return "Ab6 (closest)";
    default:   return "?";
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("========================================");
  Serial.println("  ESP32 DTMF Tone Generator");
  Serial.println("========================================");
  Serial.println("Type a digit (0-9), *, #, or A-D");
  Serial.println("in the Serial Monitor and press Enter.");
  Serial.println("Buzzer on GPIO25 (DAC1).");
  Serial.println("========================================");
  Serial.println();

  // Print DTMF frequency reference table
  Serial.println("DTMF Frequency Reference:");
  Serial.println("Key  | Low (Hz) | High (Hz)");
  Serial.println("-----|----------|----------");
  for (int i = 0; i < NUM_KEYS; i++) {
    Serial.printf("  %c  |   %4d   |   %4d\n",
                  dtmfTable[i].key,
                  dtmfTable[i].freqLow,
                  dtmfTable[i].freqHigh);
  }
  Serial.println();

  // Initialize DAC to midpoint (silence)
  dacWrite(DAC_PIN, 128);
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();

    // Skip newline/carriage return
    if (c == '\n' || c == '\r') return;

    int idx = findKey(c);
    if (idx >= 0) {
      uint16_t fLow  = dtmfTable[idx].freqLow;
      uint16_t fHigh = dtmfTable[idx].freqHigh;

      Serial.println("────────────────────────────────");
      Serial.printf("Key pressed : '%c'\n", dtmfTable[idx].key);
      Serial.printf("Low  freq   : %d Hz  [%s]\n", fLow, noteName(fLow));
      Serial.printf("High freq   : %d Hz  [%s]\n", fHigh, noteName(fHigh));
      Serial.printf("Duration    : %d ms\n", TONE_DURATION);
      Serial.println("Status      : Playing...");

      playDTMF(fLow, fHigh, TONE_DURATION);

      Serial.println("Status      : Done");
      Serial.println("────────────────────────────────");
      Serial.println();
    } else {
      Serial.printf("'%c' is not a valid DTMF key. Use 0-9, *, #, A-D.\n\n", c);
    }
  }
}
