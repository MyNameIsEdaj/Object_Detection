"""Main window: mascot + balloon, video screen, controls, object stickers."""
import time
from datetime import datetime

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QScrollArea, QSlider, QVBoxLayout, QWidget)

from core import DEFAULT_MODEL_PATH, PROJECT_ROOT
from core.config import CAMERA_INDICES

from . import cursors, theme
from .mascot import Mascot
from .titlebar import InkFrame, TitleBar, chicken_icon
from .video_view import VideoView
from .widgets import (ComicButton, ComicPanel, ComicSlider, HalftoneBackground, OutlinedTitle,
                      SpeechBalloon, StickerCard, ToggleSwitch)
from .worker import DetectionWorker

SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
CAMERA_NAMES = {0: "LAPTOP CAM", 1: "USB WEBCAM"}
NEW_OBJECT_GAP = 2.0   # seconds an object must be gone before it "appears" again
BALLOON_HOLD = 2.2     # seconds a special message stays up


def panel_title(text):
    lbl = QLabel(text)
    lbl.setObjectName("panelTitle")
    return lbl


def chip(text=""):
    lbl = QLabel(text)
    lbl.setObjectName("chip")
    return lbl


class MainWindow(QMainWindow):
    def __init__(self, model_path=DEFAULT_MODEL_PATH):
        super().__init__()
        self.model_path = model_path
        self.worker = None
        self.class_names = []
        self.cards = []
        self.last_seen = {}
        self.balloon_hold_until = 0.0

        self.setWindowTitle("Object Spotter!")
        self.setWindowIcon(chicken_icon())
        # our own comic title bar replaces the Windows one
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowSystemMenuHint
                            | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setMinimumSize(860, 600)
        self._build_ui()
        self.setCursor(cursors.arrow())          # comic arrow everywhere in the app
        self.camera_box.setCursor(cursors.hand())
        self.camera_box.view().setCursor(cursors.hand())
        self._build_cards(theme.DEFAULT_CLASSES)
        self._set_idle()

        for key, slot in (("Space", self.toggle_running), ("S", self.take_snapshot)):
            QShortcut(QKeySequence(key), self).activated.connect(slot)

    def fit_to_screen(self):
        """Open at a size that fits the screen (Windows display scaling included)."""
        screen = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        w = min(1280, int(screen.width() * 0.94))
        h = min(840, int(screen.height() * 0.92))
        self.resize(max(w, self.minimumWidth()), max(h, self.minimumHeight()))
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft().x(), max(screen.top(), frame.topLeft().y()))

    # -------------------------------------------------------------- layout
    def _build_ui(self):
        self.frame = InkFrame(self)
        self.setCentralWidget(self.frame)
        fl = QVBoxLayout(self.frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)
        self.title_bar = TitleBar(self)
        fl.addWidget(self.title_bar)
        root = HalftoneBackground()
        fl.addWidget(root, 1)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 10, 14, 14)
        outer.setSpacing(10)

        # header: mascot, speech balloon, title
        header = QHBoxLayout()
        self.mascot = Mascot()
        self.balloon = SpeechBalloon()
        header.addWidget(self.mascot)
        header.addWidget(self.balloon, 1)
        header.addSpacing(12)
        header.addWidget(OutlinedTitle("OBJECT SPOTTER!", theme.RED, px=40))
        outer.addLayout(header)

        # body: video (left) + controls (right)
        body = QHBoxLayout()
        body.setSpacing(16)
        screen = ComicPanel(theme.RED)
        sv = QVBoxLayout(screen)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(8)
        self.video = VideoView()
        sv.addWidget(self.video, 1)
        hud = QHBoxLayout()
        self.fps_chip, self.device_chip, self.cam_chip = chip("FPS --"), chip("DEVICE --"), chip("CAM --")
        for c in (self.fps_chip, self.device_chip, self.cam_chip):
            hud.addWidget(c)
        hud.addStretch(1)
        sv.addLayout(hud)

        body.addWidget(screen, 1)

        side = QVBoxLayout()
        side.setSpacing(10)
        side.setContentsMargins(0, 0, 6, 0)
        self.start_btn = ComicButton("START!", theme.BLUE, font_px=28)
        self.start_btn.clicked.connect(self.toggle_running)
        side.addWidget(self.start_btn)

        cam_panel = ComicPanel()
        cv = QVBoxLayout(cam_panel)
        cv.addWidget(panel_title("CAMERA"))
        self.camera_box = QComboBox()
        for idx in CAMERA_INDICES:
            self.camera_box.addItem(f"{CAMERA_NAMES.get(idx, 'CAMERA')} ({idx})", idx)
        self.camera_box.currentIndexChanged.connect(self._on_camera_picked)
        cv.addWidget(self.camera_box)
        side.addWidget(cam_panel)

        conf_panel = ComicPanel()
        confv = QVBoxLayout(conf_panel)
        row = QHBoxLayout()
        row.addWidget(panel_title("HOW SURE?"))
        row.addStretch(1)
        self.conf_label = panel_title("25%")
        row.addWidget(self.conf_label)
        confv.addLayout(row)
        self.conf_slider = ComicSlider()
        self.conf_slider.setRange(5, 95)
        self.conf_slider.setValue(25)
        self.conf_slider.valueChanged.connect(self._on_conf_changed)
        confv.addWidget(self.conf_slider)
        hint = QLabel("Higher = fewer but surer boxes")
        hint.setObjectName("hint")
        confv.addWidget(hint)
        side.addWidget(conf_panel)

        track_panel = ComicPanel()
        tv = QHBoxLayout(track_panel)
        tcol = QVBoxLayout()
        tcol.addWidget(panel_title("SMOOTH TRACKING"))
        thint = QLabel("Keeps boxes on moving objects")
        thint.setObjectName("hint")
        tcol.addWidget(thint)
        tv.addLayout(tcol, 1)
        self.track_toggle = ToggleSwitch(True)
        self.track_toggle.toggled.connect(self._on_tracking_toggled)
        tv.addWidget(self.track_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        side.addWidget(track_panel)

        self.snap_btn = ComicButton("SNAP!", theme.GREEN, theme.WHITE, font_px=22)
        self.snap_btn.clicked.connect(self.take_snapshot)
        side.addWidget(self.snap_btn)
        keys = QLabel("SPACE = start / stop     S = snap")
        keys.setObjectName("hint")
        keys.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(keys)
        side.addStretch(1)

        side_w = QWidget()
        side_w.setLayout(side)
        side_w.setAutoFillBackground(False)
        # controls scroll if the window is too short to show them all
        scroll = QScrollArea()
        scroll.setWidget(side_w)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget"
                             " { background: transparent; }")
        scroll.viewport().setAutoFillBackground(False)
        scroll.setFixedWidth(300)
        body.addWidget(scroll)
        outer.addLayout(body, 1)

        # sticker cards
        self.cards_row = QGridLayout()
        self.cards_row.setSpacing(12)
        outer.addLayout(self.cards_row)

        for btn in (self.start_btn, self.snap_btn):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for panel in root.findChildren(ComicPanel):
            panel.layout().setContentsMargins(0, 0, 0, 0)  # padding comes from the panel

    def _build_cards(self, names):
        for card in self.cards:
            card.setParent(None)
            card.deleteLater()
        self.cards = []
        self.class_names = list(names)
        for i, name in enumerate(self.class_names):
            label, color = theme.class_style(name, i)
            card = StickerCard(label, color)
            card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.cards_row.addWidget(card, 0, i)
            self.cards.append(card)

    # ------------------------------------------------------------ running
    def toggle_running(self):
        if self.worker is None:
            self.start()
        else:
            self.stop()

    def start(self):
        if self.worker is not None:
            return
        self.worker = DetectionWorker(self.model_path,
                                      self.camera_box.currentData(),
                                      self.conf_slider.value() / 100,
                                      self.track_toggle.isChecked(), self)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.model_ready.connect(self._on_model_ready)
        self.worker.camera_changed.connect(self._on_camera_changed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()
        self.start_btn.set_style("STOP!", theme.RED)
        self.mascot.set_mood(Mascot.IDLE)
        self.video.clear("WARMING UP...")
        self._say("WARMING UP MY SUPER-VISION...", hold=0)

    def stop(self):
        if self.worker is not None:
            worker, self.worker = self.worker, None
            worker.stop()
            worker.wait(4000)
            worker.deleteLater()
        self._set_idle()

    def _set_idle(self):
        self.start_btn.set_style("START!", theme.BLUE)
        self.mascot.set_mood(Mascot.SLEEP)
        self.video.clear("PRESS START!")
        self.fps_chip.setText("FPS --")
        for card in self.cards:
            card.set_count(0)
        self.last_seen.clear()
        self.balloon_hold_until = 0.0
        self._say("ZZZ... PRESS START, HERO!", hold=0)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.update_state()
            self.frame.set_border(not self.isMaximized())
        super().changeEvent(event)

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(4000)
        super().closeEvent(event)

    # ------------------------------------------------------------ signals
    def _on_model_ready(self, names, device):
        if names != self.class_names:
            self._build_cards(names)
        self.device_chip.setText(device.upper())

    def _on_camera_changed(self, index, ok):
        self.cam_chip.setText(f"CAM {index}")
        pos = self.camera_box.findData(index)
        if pos >= 0 and pos != self.camera_box.currentIndex():
            self.camera_box.blockSignals(True)
            self.camera_box.setCurrentIndex(pos)
            self.camera_box.blockSignals(False)
        if not ok:
            self._say(f"NO CAMERA THERE! USING CAM {index}.")

    def _on_failed(self, message):
        self.stop()
        self._say("UH-OH! SOMETHING WENT WRONG!")
        QMessageBox.warning(self, "Object Spotter", message)

    def _on_camera_picked(self, _):
        if self.worker is not None:
            self.worker.request_camera(self.camera_box.currentData())
            self._say("SWITCHING CAMERAS...")

    def _on_conf_changed(self, value):
        self.conf_label.setText(f"{value}%")
        if self.worker is not None:
            self.worker.conf = value / 100

    def _on_tracking_toggled(self, on):
        if self.worker is not None:
            self.worker.use_tracking = on
        self._say("SMOOTH TRACKING ON!" if on else "RAW DETECTION MODE!")

    def _on_frame(self, image, dets, stats):
        if self.worker is None:
            return  # late frame after Stop
        shown = [d for d in dets if 0 <= d[2] < len(self.cards) and self.cards[d[2]].isChecked()]
        self.video.set_frame(image, shown)
        self.fps_chip.setText(f"FPS {stats['fps']:.0f}")

        counts = [0] * len(self.cards)
        for d in shown:
            counts[d[2]] += 1
        for card, n in zip(self.cards, counts):
            card.set_count(n if card.isChecked() else 0)
        self._react(shown, counts)

    # ----------------------------------------------------------- reactions
    def _react(self, dets, counts):
        now = time.monotonic()
        newcomer = None
        for cid, n in enumerate(counts):
            if n == 0:
                continue
            if now - self.last_seen.get(cid, -1e9) > NEW_OBJECT_GAP and newcomer is None:
                newcomer = cid
            self.last_seen[cid] = now

        if newcomer is not None:
            box = max((d[0] for d in dets if d[2] == newcomer), key=lambda b: b[2] * b[3])
            label, color = theme.class_style(self.class_names[newcomer], newcomer)
            self.video.add_burst(box[0] + box[2] / 2, box[1] + box[3] / 2, color)
            self.mascot.set_mood(Mascot.EXCITED)
            self._say(f"KA-POW! A WILD {label}!")
            return

        if now < self.balloon_hold_until:
            return
        parts = []
        for cid, n in enumerate(counts):
            if n:
                label, _ = theme.class_style(self.class_names[cid], cid)
                parts.append(f"{n} {theme.plural(label, n)}")
        if not parts:
            self._say("HMM... SHOW ME SOMETHING!", hold=0)
        else:
            text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " AND " + parts[-1]
            self._say(f"I SEE {text}!", hold=0)

    def _say(self, text, hold=BALLOON_HOLD):
        self.balloon.set_text(text)
        if hold:
            self.balloon_hold_until = time.monotonic() + hold

    def take_snapshot(self):
        img = self.video.snapshot()
        if img is None:
            self._say("START THE CAMERA FIRST!")
            return
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        path = SNAPSHOT_DIR / f"snapshot_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        if img.save(str(path), "JPG", 92):
            self.video.flash()
            self.mascot.set_mood(Mascot.EXCITED)
            self._say(f"SNAP! SAVED {path.name}")
        else:
            self._say("OOPS! COULDN'T SAVE THE PHOTO.")
