"""Sound effects and background music for the active theme, each with a remembered on/off.

Sound effects: gui/sounds/<theme>/<name>.wav (made by gui/sounds/make_sounds.py):
click, start, stop, new, mascot, snap, theme.
Background music: gui/sounds/<THEME>.mp3 (COMIC.mp3, CANDY.mp3; .wav/.ogg/.m4a also work).
"""
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSettings, QUrl, QVariantAnimation

from . import theme

SOUND_DIR = Path(__file__).resolve().parent / "sounds"
MIN_GAP = {"new": 0.35, "mascot": 0.8}  # seconds between repeats, so it never gets noisy

MUSIC_VOLUME = 0.30                          # background music sits under the sound effects
MUSIC_GAIN = {"comic": 0.50, "candy": 0.38}  # evens out the two tracks' loudness
MUSIC_EXTS = (".mp3", ".wav", ".ogg", ".m4a")

try:  # Qt's players (part of the normal PySide6 install)
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
except Exception:  # pragma: no cover - fall back to Windows' built-in player (no music)
    QAudioOutput = QMediaPlayer = QSoundEffect = None


class SoundBoard:
    def __init__(self, volume=0.7):
        self.volume = volume
        self._settings = QSettings("ObjectSpotter", "ObjectSpotter")
        self.muted = str(self._settings.value("muted", "false")).lower() == "true"
        self._effects = {}
        self._last = {}

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._settings.setValue("muted", "true" if self.muted else "false")

    def toggle_mute(self):
        self.set_muted(not self.muted)
        return self.muted

    def path(self, name):
        return SOUND_DIR / theme.NAME / f"{name}.wav"

    def play(self, name):
        if self.muted:
            return
        now = time.monotonic()
        if now - self._last.get(name, 0) < MIN_GAP.get(name, 0.05):
            return
        self._last[name] = now
        path = self.path(name)
        if not path.exists():
            return
        if QSoundEffect is not None:
            key = (theme.NAME, name)
            fx = self._effects.get(key)
            if fx is None:
                fx = QSoundEffect()
                fx.setSource(QUrl.fromLocalFile(str(path)))
                self._effects[key] = fx
            fx.setVolume(self.volume)
            fx.play()
        elif sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)

    def preload(self):
        """Load this theme's sounds now so the first play has no delay."""
        if QSoundEffect is None:
            return
        for wav in (SOUND_DIR / theme.NAME).glob("*.wav"):
            key = (theme.NAME, wav.stem)
            if key not in self._effects:
                fx = QSoundEffect()
                fx.setSource(QUrl.fromLocalFile(str(wav)))
                self._effects[key] = fx


def _setting_on(settings, key, default=True):
    return str(settings.value(key, "true" if default else "false")).lower() == "true"


class MusicPlayer:
    """Loops the active theme's background track, fading between tracks."""

    def __init__(self):
        self._settings = QSettings("ObjectSpotter", "ObjectSpotter")
        self.enabled = _setting_on(self._settings, "music", True)
        self.available = QMediaPlayer is not None
        self._theme = None
        self._fade = None
        if self.available:
            self._out = QAudioOutput()
            self._out.setVolume(0.0)
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._out)
            try:
                self._player.setLoops(QMediaPlayer.Loops.Infinite)
            except Exception:  # older Qt: restart by hand at the end
                self._player.mediaStatusChanged.connect(self._loop_by_hand)

    @staticmethod
    def track_for(name):
        for f in SOUND_DIR.iterdir() if SOUND_DIR.is_dir() else ():
            if f.is_file() and f.stem.lower() == name and f.suffix.lower() in MUSIC_EXTS:
                return f
        return None

    def _target_volume(self):
        return MUSIC_VOLUME * MUSIC_GAIN.get(theme.NAME, 1.0)

    def _loop_by_hand(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.setPosition(0)
            self._player.play()

    def _fade_to(self, volume, ms, then=None):
        if self._fade is not None:
            self._fade.stop()
        self._fade = QVariantAnimation()
        self._fade.setDuration(ms)
        self._fade.setStartValue(float(self._out.volume()))
        self._fade.setEndValue(float(volume))
        self._fade.valueChanged.connect(lambda v: self._out.setVolume(float(v)))
        if then:
            self._fade.finished.connect(then)
        self._fade.start()

    def sync(self):
        """Play the active theme's track (or stop) to match the theme and the on/off setting."""
        if not self.available:
            return
        if not self.enabled:
            self._fade_to(0.0, 400, self._player.pause)
            return
        track = self.track_for(theme.NAME)
        if track is None:
            self._fade_to(0.0, 400, self._player.stop)
            self._theme = None
            return
        if self._theme == theme.NAME:
            if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self._player.play()
            self._fade_to(self._target_volume(), 600)
            return

        def start_new():
            self._theme = theme.NAME
            self._player.setSource(QUrl.fromLocalFile(str(track)))
            self._player.play()
            self._fade_to(self._target_volume(), 900)

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._fade_to(0.0, 350, start_new)   # fade the old track out first
        else:
            self._out.setVolume(0.0)
            start_new()

    def toggle(self):
        self.enabled = not self.enabled
        self._settings.setValue("music", "true" if self.enabled else "false")
        self.sync()
        return self.enabled
