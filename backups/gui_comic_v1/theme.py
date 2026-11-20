"""Comic pop theme: colours, fonts, stylesheet and comic phrases."""
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

INK = QColor("#111111")
PAPER = QColor("#FFE14D")      # halftone yellow background
RED = QColor("#FF3B3B")
BLUE = QColor("#2F80ED")
GREEN = QColor("#3DDC84")
WHITE = QColor("#FFFFFF")
SCREEN = QColor("#2B2B2B")     # empty video area

# label shown in the UI + colour, per model class name
CLASS_STYLE = {
    "can": ("CAN", "#FF8A00"),
    "glasses": ("GLASSES", "#FF4FB0"),
    "marker": ("MARKER", "#3DDC84"),
    "watch": ("WATCH", "#2F80ED"),
    "water bottle": ("BOTTLE", "#9B51E0"),
}
FALLBACK_COLORS = ["#FF8A00", "#FF4FB0", "#3DDC84", "#2F80ED", "#9B51E0", "#00B8D4"]
DEFAULT_CLASSES = list(CLASS_STYLE)  # used until the model reports its own names

EXCLAIMS = ["POW!", "BAM!", "ZAP!", "WHAM!", "BOOM!", "KAPOW!", "ZOINKS!"]

FONT_DIR = Path(__file__).resolve().parent / "fonts"
DISPLAY_FAMILY = "Impact"
BODY_FAMILY = "Comic Sans MS"


def class_style(name, cls_id=0):
    label, color = CLASS_STYLE.get(name.lower(), (name.upper(), None))
    return label, QColor(color or FALLBACK_COLORS[cls_id % len(FALLBACK_COLORS)])


def plural(label, n):
    if n == 1 or label.endswith("S"):
        return label
    if label.endswith(("CH", "SH", "X")):
        return label + "ES"
    return label + "S"


def load_fonts():
    """Use comic fonts dropped into gui/fonts (e.g. Bangers.ttf, ComicNeue-Bold.ttf),
    otherwise fall back to fonts that ship with Windows."""
    global DISPLAY_FAMILY, BODY_FAMILY
    if FONT_DIR.is_dir():
        for f in list(FONT_DIR.glob("*.ttf")) + list(FONT_DIR.glob("*.otf")):
            QFontDatabase.addApplicationFont(str(f))
    available = set(QFontDatabase.families())

    def first(*names):
        return next((n for n in names if n in available), names[-1])

    DISPLAY_FAMILY = first("Bangers", "Luckiest Guy", "Impact", "Arial Black", "Arial")
    BODY_FAMILY = first("Comic Neue", "Comic Sans MS", "Segoe UI", "Arial")


def display_font(px):
    f = QFont(DISPLAY_FAMILY)
    f.setPixelSize(int(px))
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
    return f


def body_font(px, bold=True):
    f = QFont(BODY_FAMILY)
    f.setPixelSize(int(px))
    f.setBold(bold)
    return f


def stylesheet():
    return f"""
    QWidget {{ font-family: "{BODY_FAMILY}"; color: #111111; }}
    QLabel#chip {{
        background: #FFFFFF; border: 3px solid #111111; border-radius: 12px;
        padding: 2px 10px; font-size: 13px; font-weight: bold;
    }}
    QLabel#panelTitle {{ font-family: "{DISPLAY_FAMILY}"; font-size: 20px; letter-spacing: 1px; }}
    QLabel#hint {{ font-size: 12px; font-weight: bold; color: #333333; }}
    QComboBox {{
        background: #FFFFFF; border: 3px solid #111111; border-radius: 10px;
        padding: 4px 10px; font-size: 14px; font-weight: bold; min-height: 24px;
    }}
    QComboBox::drop-down {{ border: 0px; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: #FFFFFF; border: 3px solid #111111; font-weight: bold;
        selection-background-color: #FFE14D; selection-color: #111111;
    }}
    QScrollBar:vertical {{
        background: #FFFFFF; width: 14px; border: 2px solid #111111; border-radius: 7px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #FF3B3B; border: 2px solid #111111; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QToolTip {{
        background: #FFFFFF; color: #111111; border: 2px solid #111111;
        font-weight: bold; padding: 4px;
    }}
    """
