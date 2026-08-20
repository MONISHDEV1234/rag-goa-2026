#!/usr/bin/env python3
"""
scripts/generate_test_audio.py — Generate synthetic test WAV files for benchmark queries (Role 2)

Generates small, valid 16kHz mono WAV files for each query in queries.json
so that the audio/STT pipeline can be tested in automated benchmarks and CI
without requiring manual microphone inputs.
"""

import json
import math
import struct
import wave
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
QUERIES_FILE = ROOT_DIR / "benchmarks" / "queries.json"
AUDIO_DIR = ROOT_DIR / "benchmarks" / "audio"


def generate_sine_wave(
    filename: Path,
    duration_s: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> None:
    """Generate a simple 16kHz mono 16-bit PCM WAV file."""
    filename.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_s * sample_rate)
    
    with wave.open(str(filename), "wb") as wav_file:
        wav_file.setnchannels(1)        # mono
        wav_file.setsampwidth(2)       # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            # Sine wave with gentle fade-in / fade-out to prevent clicks
            envelope = min(1.0, i / 500.0, (num_samples - i) / 500.0)
            sample = int(32767.0 * 0.3 * envelope * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
            frames.extend(struct.pack("<h", sample))
            
        wav_file.writeframes(frames)


def main() -> None:
    if not QUERIES_FILE.exists():
        print(f"Error: {QUERIES_FILE} not found.")
        return

    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        queries = json.load(f)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating synthetic audio for {len(queries)} benchmark queries in {AUDIO_DIR}...")

    for item in queries:
        qid = item["id"]
        out_file = AUDIO_DIR / f"{qid}.wav"
        # Vary frequency slightly by query id so files are distinct
        freq = 300.0 + (qid * 7) % 500
        generate_sine_wave(out_file, duration_s=1.5, frequency=freq)

    print(f"Successfully generated {len(queries)} WAV files in {AUDIO_DIR}.")


if __name__ == "__main__":
    main()
