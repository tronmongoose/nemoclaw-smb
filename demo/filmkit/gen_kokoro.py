import os
from kokoro_onnx import Kokoro
import soundfile as sf

os.makedirs("/tmp/nemo-film/aud", exist_ok=True)
k = Kokoro("/tmp/nemo-film/kokoro-v1.0.onnx", "/tmp/nemo-film/voices-v1.0.bin")
VOICE = "af_heart"

texts = [
    "NemoClaw. An A.I. operations layer for short-term rental managers, with Nous Hermes handling the coordination.",
    "Every property runs a turnover loop. Checkout, clean, inspect, ready to book. Here the agent has flagged Sweet Clementine as stalled. The inspection never started.",
    "When a handoff stalls, Hermes drafts the nudge to the person who is blocking it. This is a live model call, not a script.",
    "For a stuck cleaning, Hermes finds a free cleaner, proposes a time, and with one click reassigns the job and pre-authorizes a single-use card.",
    "Across the portfolio, it flags which properties are over or under performing, and Hermes explains why in plain language.",
    "The whole book of business is a live graph. The firm, its owners, every property, and the cleaning crew, all connected.",
    "Every action runs as a named agent on an audited floor. Coordination, scheduling, performance, and payments.",
    "The owner sees the same turnover loop for their property, so nothing falls through the cracks.",
    "The same agent sells its skills to other agents. Marketing audits, guest replies, and pricing, each one paid for per call.",
    "Every call settles over the HTTP four oh two payment standard. This is the live marketplace, where agents earn from other agents.",
    "One property manager. Many agents. Hermes connects the work.",
]

for i, t in enumerate(texts):
    samples, sr = k.create(t, voice=VOICE, speed=1.0, lang="en-us")
    sf.write(f"/tmp/nemo-film/aud/s{i}.wav", samples, sr)
    print(f"s{i} ok {len(samples)/sr:.1f}s")
print("KOKORO_DONE")
