"""Themes: colours, fonts, shapes and phrases. Two themes: "comic" and "candy".

Colours are QColor objects that apply() updates *in place*, so every widget
that already holds one of them follows the active theme.
"""
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

THEMES = {
    "comic": {
        "label": "Comic pop",
        "colors": {
            "INK": "#111111",      # outlines and lettering stroke
            "SHADOW": "#111111",   # solid offset shadows
            "PAPER": "#FFE14D",    # page background
            "RED": "#FF3B3B",      # title bar, STOP, accents
            "BLUE": "#2F80ED",     # START
            "GREEN": "#3DDC84",    # SNAP!, switch on
            "WHITE": "#FFFFFF",
            "SCREEN": "#2B2B2B",   # empty video area
            "BEAK": "#FFB020",
            "CHEEK": "#FF9EC7",
            "MASCOT_BODY": "#FFFFFF",
            "DOT": "#11111126",    # background pattern (#RRGGBBAA)
        },
        "classes": {
            "can": ("CAN", "#FF8A00"),
            "glasses": ("GLASSES", "#FF4FB0"),
            "marker": ("MARKER", "#3DDC84"),
            "watch": ("WATCH", "#2F80ED"),
            "water bottle": ("BOTTLE", "#9B51E0"),
        },
        "display_fonts": ["Bangers", "Luckiest Guy", "Impact", "Arial Black", "Arial"],
        "body_fonts": ["Comic Neue", "Comic Sans MS", "Segoe UI", "Arial"],
        "round": 1.0,          # corner roundness multiplier
        "background": "halftone",
        "mascot": "chicken",
        "burst_spikes": 14,
        "exclaims": ["POW!", "BAM!", "ZAP!", "WHAM!", "BOOM!", "KAPOW!", "ZOINKS!"],
        "say": {
            "sleep": "ZZZ... PRESS START, HERO!",
            "warming": "WARMING UP MY SUPER-VISION...",
            "nothing": "HMM... SHOW ME SOMETHING!",
            "new": "KA-POW! A WILD {}!",
            "see": "I SEE {}!",
        },
    },
    "candy": {
        "label": "Candy pop",
        "colors": {
            "INK": "#7A2A5A",      # plum outlines
            "SHADOW": "#E58BB8",   # soft pink shadows
            "PAPER": "#FFE3F1",
            "RED": "#FF6FAE",      # bubblegum pink
            "BLUE": "#5FCFBC",     # mint
            "GREEN": "#A8DE6A",    # sour-apple green
            "WHITE": "#FFFFFF",
            "SCREEN": "#5E3D6E",
            "BEAK": "#FFB86B",
            "CHEEK": "#FF9EC7",
            "MASCOT_BODY": "#FF8FC4",
            "DOT": "#FF6FAE80",
        },
        "classes": {
            "can": ("CAN", "#FFA36B"),
            "glasses": ("GLASSES", "#FF7FD0"),
            "marker": ("MARKER", "#6FD48A"),
            "watch": ("WATCH", "#6CC4FF"),
            "water bottle": ("BOTTLE", "#B38CFF"),
        },
        "display_fonts": ["Fredoka", "Fredoka One", "Baloo 2", "Arial Rounded MT Bold",
                          "Segoe UI Black", "Arial"],
        "body_fonts": ["Fredoka", "Nunito", "Arial Rounded MT Bold", "Segoe UI", "Arial"],
        "round": 1.9,
        "background": "sprinkles",
        "mascot": "bear",
        "burst_spikes": 10,
        "exclaims": ["YAY!", "SWEET!", "POP!", "YUM!", "WOW!", "HOORAY!"],
        "say": {
            "sleep": "ZZZ... PRESS START, SWEETIE!",
            "warming": "UNWRAPPING MY CANDY-VISION...",
            "nothing": "MMM... SHOW ME A TREAT!",
            "new": "YAY~ A SWEET {}!",
            "see": "I SEE {}!",
        },
    },
}
DEFAULT_THEME = "comic"

# ---- active theme values (filled in by apply) ------------------------------
NAME = DEFAULT_THEME
LABEL = ""
INK, SHADOW, PAPER, RED, BLUE, GREEN, WHITE, SCREEN = (QColor() for _ in range(8))
BEAK, CHEEK, MASCOT_BODY, DOT = (QColor() for _ in range(4))
CLASS_STYLE = {}
FALLBACK_COLORS = ["#FF8A00", "#FF4FB0", "#3DDC84", "#2F80ED", "#9B51E0", "#00B8D4"]
DEFAULT_CLASSES = ["can", "glasses", "marker", "watch", "water bottle"]
EXCLAIMS = []
SAY = {}
ROUND = 1.0
BACKGROUND = "halftone"
MASCOT = "chicken"
BURST_SPIKES = 14

FONT_DIR = Path(__file__).resolve().parent / "fonts"
DISPLAY_FAMILY = "Impact"
BODY_FAMILY = "Comic Sans MS"
_fonts_registered = False


def _set(color, value):
    v = value.lstrip("#")
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    a = int(v[6:8], 16) if len(v) == 8 else 255
    color.setRgb(r, g, b, a)


def apply(name):
    """Switch the active theme (call before building windows)."""
    global NAME, LABEL, CLASS_STYLE, EXCLAIMS, SAY, ROUND, BACKGROUND, MASCOT, BURST_SPIKES
    name = name if name in THEMES else DEFAULT_THEME
    t = THEMES[name]
    NAME, LABEL = name, t["label"]
    g = globals()
    for key, value in t["colors"].items():
        _set(g[key], value)
    CLASS_STYLE = dict(t["classes"])
    EXCLAIMS = list(t["exclaims"])
    SAY = dict(t["say"])
    ROUND = t["round"]
    BACKGROUND = t["background"]
    MASCOT = t["mascot"]
    BURST_SPIKES = t["burst_spikes"]
    _pick_fonts(t)
    return name


def next_theme(name=None):
    names = list(THEMES)
    return names[(names.index(name or NAME) + 1) % len(names)]




def class_style(name, cls_id=0):
    label, color = CLASS_STYLE.get(name.lower(), (name.upper(), None))
    return label, QColor(color or FALLBACK_COLORS[cls_id % len(FALLBACK_COLORS)])


def plural(label, n):
    if n == 1 or label.endswith("S"):
        return label
    if label.endswith(("CH", "SH", "X")):
        return label + "ES"
    return label + "S"


def r(radius):
    """Corner radius adjusted for the active theme (candy is rounder)."""
    return radius * ROUND


# ----------------------------------------------------------------------- fonts
def load_fonts():
    """Register fonts dropped into gui/fonts and pick the best available ones.
    Needs a QApplication."""
    global _fonts_registered
    if not _fonts_registered and FONT_DIR.is_dir():
        for f in list(FONT_DIR.glob("*.ttf")) + list(FONT_DIR.glob("*.otf")):
            QFontDatabase.addApplicationFont(str(f))
    _fonts_registered = True
    _pick_fonts(THEMES[NAME])


def _pick_fonts(t):
    global DISPLAY_FAMILY, BODY_FAMILY
    if not _fonts_registered:
        return  # no QApplication yet; load_fonts() will do it
    available = set(QFontDatabase.families())

    def first(names):
        return next((n for n in names if n in available), names[-1])

    DISPLAY_FAMILY = first(t["display_fonts"])
    BODY_FAMILY = first(t["body_fonts"])


def display_font(px):
    f = QFont(DISPLAY_FAMILY)
    f.setPixelSize(int(px))
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
    if NAME == "candy":
        f.setBold(True)
    return f


def body_font(px, bold=True):
    f = QFont(BODY_FAMILY)
    f.setPixelSize(int(px))
    f.setBold(bold)
    return f


def stylesheet():
    ink, white, paper, red = INK.name(), WHITE.name(), PAPER.name(), RED.name()
    rad = int(r(10))
    return f"""
    QWidget {{ font-family: "{BODY_FAMILY}"; color: {ink}; }}
    QLabel#chip {{
        background: {white}; border: 3px solid {ink}; border-radius: {min(11, int(r(12)))}px;
        padding: 2px 10px; font-size: 13px; font-weight: bold;
    }}
    QLabel#panelTitle {{ font-family: "{DISPLAY_FAMILY}"; font-size: 20px; letter-spacing: 1px;
        font-weight: {'bold' if NAME == 'candy' else 'normal'}; }}
    QLabel#hint {{ font-size: 12px; font-weight: bold; color: {ink}; }}
    QComboBox {{
        background: {white}; border: 3px solid {ink}; border-radius: {min(16, rad)}px;
        padding: 4px 10px; font-size: 14px; font-weight: bold; min-height: 24px;
    }}
    QComboBox::drop-down {{ border: 0px; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {white}; border: 3px solid {ink}; font-weight: bold;
        selection-background-color: {paper}; selection-color: {ink};
    }}
    QScrollBar:vertical {{
        background: {white}; width: 14px; border: 2px solid {ink}; border-radius: 7px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {red}; border: 2px solid {ink}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QToolTip {{
        background: {white}; color: {ink}; border: 2px solid {ink};
        font-weight: bold; padding: 4px;
    }}
    """


apply(DEFAULT_THEME)  # must stay at the end: it uses the functions above
