"""Generate the app's sound effects (all synthesized here, no recordings).

Run again after tweaking a recipe:
    uv run python gui/sounds/make_sounds.py

Writes gui/sounds/comic/*.wav and gui/sounds/candy/*.wav
(44.1 kHz, 16-bit mono). Needs only numpy and the standard library.
"""
import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ helpers
def t_axis(seconds):
    return np.arange(int(RATE * seconds)) / RATE


def sweep(f0, f1, seconds, shape="exp"):
    """Sine whose pitch glides from f0 to f1."""
    t = t_axis(seconds)
    k = t / seconds
    f = f0 * (f1 / f0) ** k if shape == "exp" else f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / RATE)


def env(n, attack=0.005, release=0.08, curve=3.0):
    """Quick attack, exponential-ish release."""
    e = np.ones(n)
    a = max(1, int(RATE * attack))
    e[:a] = np.linspace(0, 1, a)
    r = min(n - a, int(RATE * release))
    if r > 0:
        e[-r:] *= np.linspace(1, 0, r) ** curve
    return e


def decay(n, rate):
    return np.exp(-np.arange(n) / RATE * rate)


def lowpass(x, amount=0.15):
    """One-pole low-pass (smaller amount = darker)."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += amount * (v - acc)
        y[i] = acc
    return y


def bell(freq, seconds, rate=9.0):
    t = t_axis(seconds)
    tone = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)
            + 0.12 * np.sin(2 * np.pi * freq * 3.02 * t))
    return tone * decay(len(t), rate) * env(len(t), 0.002, 0.02)


def place(total, parts):
    """Mix (start_seconds, signal) pairs into one buffer."""
    out = np.zeros(int(RATE * total))
    for start, sig in parts:
        i = int(RATE * start)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]
    return out


def save(theme, name, x, volume=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * volume
    folder = OUT / theme
    folder.mkdir(parents=True, exist_ok=True)
    with wave.open(str(folder / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32767).astype("<i2").tobytes())


# ------------------------------------------------------------- comic sounds
def comic_click():
    n = int(RATE * 0.06)
    tok = sweep(1300, 700, 0.06) * decay(n, 70)
    return tok + 0.3 * rng.standard_normal(n) * decay(n, 400)


def comic_start():  # springy boing going up
    t = t_axis(0.45)
    f = 180 * (5.0 ** (t / 0.45)) * (1 + 0.12 * np.sin(2 * np.pi * 18 * t) * np.exp(-t * 4))
    x = np.sin(2 * np.pi * np.cumsum(f) / RATE)
    return x * env(len(t), 0.003, 0.15)


def comic_stop():  # slide whistle going down
    t = t_axis(0.5)
    f = 1400 * (0.18 ** (t / 0.5)) * (1 + 0.02 * np.sin(2 * np.pi * 6 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / RATE) + 0.15 * rng.standard_normal(len(t)) * 0.3
    return x * env(len(t), 0.02, 0.12)


def comic_new():  # POW! thump + crash
    n = int(RATE * 0.45)
    thump = sweep(140, 45, 0.45) * decay(n, 9)
    crash = lowpass(rng.standard_normal(n), 0.35) * decay(n, 11)
    snap = rng.standard_normal(n) * decay(n, 120)
    return 1.2 * thump + 0.9 * crash + 0.4 * snap


def comic_mascot():  # cartoon chicken: bok-bok-BAWK!
    def syllable(f0, f1, seconds, rough=0.25):
        t = t_axis(seconds)
        f = f0 * (f1 / f0) ** (t / seconds)
        ph = 2 * np.pi * np.cumsum(f) / RATE
        saw = 2 * ((ph / (2 * np.pi)) % 1) - 1                        # buzzy beak
        tone = 0.6 * saw + 0.4 * np.sin(ph * 2) + rough * rng.standard_normal(len(t))
        return lowpass(tone, 0.45) * env(len(t), 0.004, seconds * 0.6, 2)
    return place(0.62, [(0.00, syllable(620, 480, 0.07)),
                        (0.11, syllable(640, 500, 0.07)),
                        (0.24, syllable(950, 520, 0.34, 0.35))])


def comic_snap():  # camera shutter
    n = int(RATE * 0.03)
    clack = rng.standard_normal(n) * decay(n, 180)
    return place(0.16, [(0.0, clack), (0.07, 0.8 * clack)])


def comic_whoosh():  # (no longer used for the theme switch, kept for reference)
    n = int(RATE * 0.5)
    noise = rng.standard_normal(n)
    amt = np.linspace(0.02, 0.5, n) ** 1.5
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += amt[i] * (noise[i] - acc)
        y[i] = acc
    return y * np.sin(np.linspace(0, np.pi, n)) ** 2


def comic_theme():  # soft bubbly pop
    rng.standard_normal(int(RATE * 0.5))  # use up the old whoosh's noise so later sounds stay the same
    n1, n2 = int(RATE * 0.07), int(RATE * 0.09)
    pop = sweep(260, 820, 0.07) * env(n1, 0.002, 0.05, 2)
    bloop = sweep(700, 1100, 0.09) * env(n2, 0.003, 0.07, 2)
    return place(0.2, [(0.0, pop), (0.08, 0.7 * bloop)])


# ------------------------------------------------------------- candy sounds
C6, D6, E6, G6, A6, C7, E7, G7 = 1046.5, 1174.7, 1318.5, 1568.0, 1760.0, 2093.0, 2637.0, 3136.0


def candy_click():  # soft bloop
    n = int(RATE * 0.09)
    return sweep(520, 980, 0.09) * env(n, 0.004, 0.06, 2)


def candy_start():  # magical chime going up
    notes = [C6, E6, G6, C7]
    return place(0.75, [(i * 0.08, bell(f, 0.45)) for i, f in enumerate(notes)])


def candy_stop():  # chime going down
    notes = [C7, G6, E6, C6]
    return place(0.75, [(i * 0.08, bell(f, 0.45)) for i, f in enumerate(notes)])


def candy_new():  # twinkly glitter shimmer
    scale = [C6, D6, E6, G6, A6, C7, E7, G7]
    parts = [(rng.uniform(0, 0.55), 0.6 * bell(rng.choice(scale) * rng.choice([1, 1, 2]), 0.35, 14))
             for _ in range(16)]
    n = int(RATE * 0.9)
    sparkle = lowpass(rng.standard_normal(n), 0.9) * np.sin(np.linspace(0, np.pi, n)) ** 3 * 0.08
    return place(0.9, parts) + sparkle


def candy_mascot():  # squeaky toy "yay"
    def squeak(seconds, f0, f1, f2):
        t = t_axis(seconds)
        k = t / seconds
        f = np.where(k < 0.5, f0 + (f1 - f0) * k * 2, f1 + (f2 - f1) * (k - 0.5) * 2)
        f = f * (1 + 0.04 * np.sin(2 * np.pi * 28 * t))               # rubbery wobble
        ph = 2 * np.pi * np.cumsum(f) / RATE
        tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
        return tone * env(len(t), 0.01, seconds * 0.4, 2)
    return place(0.45, [(0.0, squeak(0.14, 1150, 1650, 1400)),
                        (0.17, squeak(0.22, 1250, 1900, 1500))])


def candy_snap():  # pop + chime
    n = int(RATE * 0.05)
    pop = sweep(300, 1400, 0.05) * env(n, 0.002, 0.04)
    return place(0.5, [(0.0, pop), (0.05, 0.7 * bell(G6, 0.4)), (0.11, 0.6 * bell(C7, 0.4))])


def candy_theme():  # quick two-note twinkle
    return place(0.45, [(0.0, 0.8 * bell(G6, 0.3, 12)), (0.07, bell(C7, 0.35, 11))])


SOUNDS = {
    "comic": {"click": comic_click, "start": comic_start, "stop": comic_stop, "new": comic_new,
              "mascot": comic_mascot, "snap": comic_snap, "theme": comic_theme},
    "candy": {"click": candy_click, "start": candy_start, "stop": candy_stop, "new": candy_new,
              "mascot": candy_mascot, "snap": candy_snap, "theme": candy_theme},
}
VOLUME = {"click": 0.45, "theme": 0.4, "snap": 0.7, "start": 0.5, "stop": 0.5, "mascot": 0.65}

if __name__ == "__main__":
    for theme, recipes in SOUNDS.items():
        for name, make in recipes.items():
            save(theme, name, make(), VOLUME.get(name, 0.8))
            print(f"wrote {theme}/{name}.wav")
