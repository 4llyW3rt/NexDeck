# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Klasik (PyQt) görünüm: stil sayfası ve özel bileşenler."""
from . import state
from .core import (  # noqa: F401
    QColor,
    QCursor,
    QEasingCurve,
    QFont,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPainter,
    QPen,
    QPropertyAnimation,
    QPushButton,
    QScrollArea,
    QTimer,
    QVBoxLayout,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from .webserver import (  # noqa: F401
    html_escape,
)

# =========================================================
# 7. ARAYÜZ (UI) VE ANA UYGULAMA SINIFI
# =========================================================
def get_stylesheet(accent_color):
    return f"""
    * {{
        font-family: 'Segoe UI';
        outline: none;
    }}

    QMainWindow, QWidget {{
        background-color: #070B14;
        color: #F8FAFC;
        font-size: 14px;
    }}

    QLabel {{
        background: transparent;
    }}

    QWidget#AppRoot, QWidget#ContentRoot, QStackedWidget#MainStack {{
        background-color: #070B14;
    }}

    QWidget#MainPage, QWidget#PageSurface {{
        background-color: #070B14;
    }}

    QWidget#SideRail {{
        background-color: #0B1220;
        border: 1px solid #1C2638;
        border-radius: 30px;
    }}

    QLabel#BrandTitle {{
        color: #FFFFFF;
        font-size: 25px;
        font-weight: 900;
        letter-spacing: 1px;
    }}

    QLabel#BrandSub {{
        color: #748298;
        font-size: 12px;
        font-weight: 700;
    }}

    QLabel#PageTitle {{
        color: #FFFFFF;
        font-size: 28px;
        font-weight: 900;
    }}

    QLabel#PageSubtitle {{
        color: #94A3B8;
        font-size: 13px;
        font-weight: 600;
    }}

    QLabel#SectionTitle {{
        color: #FFFFFF;
        font-size: 17px;
        font-weight: 900;
        background: transparent;
    }}

    QLabel#Muted {{
        color: #94A3B8;
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#StatusPill {{
        color: #94A3B8;
        background-color: #111827;
        border: 1px solid #263244;
        border-radius: 16px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 800;
    }}

    QWidget#GlassCard, QFrame#GlassCard {{
        background-color: #0E1625;
        border: 1px solid #1E2A3D;
        border-radius: 28px;
    }}

    QWidget#Topbar {{
        background-color: #0E1625;
        border: 1px solid #1E2A3D;
        border-radius: 24px;
    }}

    QWidget#HeroCard {{
        background-color: #101A2D;
        border: 1px solid #26364F;
        border-radius: 28px;
    }}

    QPushButton {{
        background-color: #182235;
        color: #F8FAFC;
        border: 1px solid #28364D;
        border-radius: 14px;
        padding: 11px 14px;
        font-weight: 800;
    }}

    QPushButton:hover {{
        background-color: {accent_color};
        border-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton:pressed {{
        background-color: #0F172A;
        padding-top: 12px;
        padding-bottom: 10px;
    }}

    QPushButton#NavBtn {{
        background-color: transparent;
        color: #8B98AA;
        border: none;
        border-radius: 18px;
        padding: 14px 12px;
        font-size: 14px;
        text-align: left;
        font-weight: 900;
    }}

    QPushButton#NavBtn:hover {{
        background-color: #121D2F;
        color: #FFFFFF;
    }}

    QPushButton#NavBtn:checked {{
        background-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton#IconBtn {{
        background-color: #111827;
        color: #CBD5E1;
        border: 1px solid #263244;
        border-radius: 16px;
        min-width: 46px;
        min-height: 44px;
        font-size: 18px;
        font-weight: 800;
        padding: 0;
    }}

    QPushButton#IconBtn:hover {{
        color: #FFFFFF;
        background-color: {accent_color};
        border-color: {accent_color};
    }}

    QPushButton#SettingsTopBtn {{
        background-color: #111827;
        color: #CBD5E1;
        border: 1px solid #263244;
        border-radius: 16px;
        min-height: 44px;
        padding-left: 16px;
        padding-right: 16px;
        font-size: 13px;
        font-weight: 900;
    }}

    QPushButton#SettingsTopBtn:hover {{
        background-color: {accent_color};
        color: #FFFFFF;
        border-color: {accent_color};
    }}

    QPushButton#ConnectBtn {{
        background-color: #10B981;
        color: white;
        border-color: #10B981;
        padding-left: 18px;
        padding-right: 18px;
    }}

    QPushButton#FloatingSettingsBtn {{
        background-color: #0F172A;
        color: #FFFFFF;
        border: 1px solid #2A3C59;
        border-radius: 23px;
        padding-left: 14px;
        padding-right: 14px;
        font-size: 14px;
        font-weight: 900;
        text-align: left;
    }}

    QPushButton#FloatingSettingsBtn:hover {{
        background-color: #162238;
        border-color: {accent_color};
    }}

    QPushButton#DisconnectBtn {{
        background-color: #EF4444;
        color: white;
        border-color: #EF4444;
        padding-left: 18px;
        padding-right: 18px;
    }}

    QPushButton#SaveBtn {{
        background-color: {accent_color};
        color: #FFFFFF;
        border: 1px solid {accent_color};
        border-radius: 18px;
        padding: 15px 20px;
        font-size: 15px;
        font-weight: 900;
    }}

    QPushButton#DangerBtn {{
        background-color: #EF4444;
        color: #FFFFFF;
        border-color: #EF4444;
    }}

    QListWidget {{
        background-color: #0B1220;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        padding: 10px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 15px 14px;
        margin: 4px;
        border-radius: 14px;
        color: #CBD5E1;
        font-weight: 800;
    }}

    QListWidget::item:hover {{
        background-color: {accent_color};
        color: #FFFFFF;
    }}

    QListWidget::item:selected {{
        background-color: {accent_color};
        color: #FFFFFF;
        border: 1px solid rgba(255,255,255,0.30);
    }}

    QGroupBox {{
        background-color: #0B1220;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        margin-top: 14px;
        padding: 20px 16px 16px 16px;
        font-weight: 900;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 18px;
        top: 5px;
        padding: 0 8px;
        color: #FFFFFF;
        background-color: #0B1220;
    }}

    QComboBox, QLineEdit {{
        background-color: #080D16;
        color: #F8FAFC;
        border: 1px solid #27354A;
        border-radius: 14px;
        padding: 11px 12px;
        font-weight: 700;
        selection-background-color: {accent_color};
    }}

    QComboBox:hover, QLineEdit:hover {{
        border-color: {accent_color};
        background-color: #111B2E;
    }}

    QComboBox:focus, QLineEdit:focus {{
        border-color: {accent_color};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox QAbstractItemView {{
        background-color: #0B1220;
        color: #F8FAFC;
        border: 1px solid #27354A;
        selection-background-color: {accent_color};
        padding: 6px;
    }}

    QTextEdit {{
        background-color: #050914;
        color: #22C55E;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        font-family: 'Consolas';
        padding: 16px;
    }}

    QScrollArea {{
        background: transparent;
        border: none;
    }}


    QScrollBar:vertical {{
        background-color: #0B1220;
        width: 12px;
        margin: 8px 2px 8px 2px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical {{
        background-color: #334155;
        min-height: 42px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {accent_color};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        background: transparent;
        border: none;
    }}

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background-color: #0B1220;
        height: 12px;
        margin: 2px 8px 2px 8px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: #334155;
        min-width: 42px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {accent_color};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        background: transparent;
        border: none;
    }}

    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}


    QSplitter::handle {{
        background-color: transparent;
        width: 12px;
        height: 12px;
    }}

    QFrame#ScreenFrame {{
        border-radius: 28px;
        border: 8px solid #070B14;
    }}

    QPushButton#ScreenBtn {{
        background-color: rgba(8, 13, 22, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 20px;
        color: #FFFFFF;
        font-weight: 900;
        font-size: 13px;
        min-height: 78px;
    }}

    QPushButton#ScreenBtn:hover {{
        background-color: {accent_color};
        border-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton#ScreenBtn:disabled {{
        background-color: #0F172A;
        border: 1px solid #334155;
        color: #64748B;
    }}
    """


class ColorNavButton(QFrame):
    clicked = pyqtSignal()

    def __init__(self, badge_text, badge_color, label, parent=None):
        super().__init__(parent)
        self._checked = False
        self.badge_color = badge_color
        self.setObjectName("ColorNavButton")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(56)
        self.setMaximumHeight(56)
        self.nav_anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.nav_anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.nav_anim_min, self.nav_anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.badge = QLabel(badge_text)
        self.badge.setFixedSize(32, 32)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet(
            f"background-color: {badge_color}; color: white; border-radius: 11px; font-size: 15px; font-weight: 900;"
        )

        self.label = QLabel(label)
        self.label.setStyleSheet("color: #A9B7CA; font-size: 14px; font-weight: 800; background: transparent;")

        layout.addWidget(self.badge)
        layout.addWidget(self.label)
        layout.addStretch()
        self.refresh_style()

    def setChecked(self, checked):
        self._checked = checked
        self.refresh_style()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._checked:
            self.animate_height(62)
            self.setStyleSheet(
                f"QFrame#ColorNavButton {{ background-color: {self.badge_color}; border: 1px solid {self.badge_color}; border-radius: 16px; }}"
            )
            self.label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._checked:
            self.animate_height(56)
            self.refresh_style()
        super().leaveEvent(event)

    def animate_height(self, target):
        for anim, prop_getter in ((self.nav_anim_min, self.minimumHeight), (self.nav_anim_max, self.maximumHeight)):
            anim.stop()
            anim.setStartValue(prop_getter())
            anim.setEndValue(target)
            anim.start()

    def refresh_style(self):
        if self._checked:
            self.animate_height(62)
            self.setStyleSheet(
                f"QFrame#ColorNavButton {{ background-color: {self.badge_color}; border: 1px solid {self.badge_color}; border-radius: 16px; }}"
            )
            self.label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; background: transparent;")
        else:
            self.animate_height(56)
            self.setStyleSheet(
                "QFrame#ColorNavButton { background-color: transparent; border: 1px solid transparent; border-radius: 16px; }"
            )
            self.label.setStyleSheet("color: #A9B7CA; font-size: 14px; font-weight: 800; background: transparent;")




class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self.accent = accent or "#3B82F6"
        self._base_min_height = 0
        self.anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.anim_min, self.anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)
        self.apply_default_style()

    def accent_color(self):
        try:
            return self.accent() if callable(self.accent) else self.accent
        except Exception:
            return "#3B82F6"

    def apply_default_style(self):
        accent = self.accent_color()
        self.setStyleSheet(
            f"background-color: #111827; color: #FFFFFF; border: 1px solid {accent}; border-radius: 18px; "
            "padding: 14px 18px; font-size: 15px; font-weight: 800;"
        )

    def apply_hover_style(self):
        accent = self.accent_color()
        self.setStyleSheet(
            f"background-color: {accent}; color: #FFFFFF; border: 1px solid {accent}; border-radius: 18px; "
            "padding: 14px 18px; font-size: 15px; font-weight: 800;"
        )

    def setHoverHeights(self, base_height, grow_by=6):
        self._base_min_height = base_height
        self._grow_by = grow_by
        self.setMinimumHeight(base_height)
        self.setMaximumHeight(base_height + 24)

    def enterEvent(self, event):
        self.apply_hover_style()
        if self._base_min_height:
            for anim, getter in ((self.anim_min, self.minimumHeight), (self.anim_max, self.maximumHeight)):
                anim.stop()
                anim.setStartValue(getter())
                anim.setEndValue(self._base_min_height + self._grow_by)
                anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_default_style()
        if self._base_min_height:
            for anim, getter in ((self.anim_min, self.minimumHeight), (self.anim_max, self.maximumHeight)):
                anim.stop()
                anim.setStartValue(getter())
                anim.setEndValue(self._base_min_height)
                anim.start()
        super().leaveEvent(event)


class HoverScaleFrame(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None, grow_by=10):
        super().__init__(parent)
        self._base_min_height = 0
        self._grow_by = grow_by
        self.setMouseTracking(True)
        self.anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.anim_min, self.anim_max):
            anim.setDuration(240)
            anim.setEasingCurve(QEasingCurve.OutCubic)

    def setHoverHeights(self, base_height, grow_by=None):
        self._base_min_height = base_height
        if grow_by is not None:
            self._grow_by = grow_by
        self.setMinimumHeight(base_height)
        self.setMaximumHeight(base_height + 80)

    def enterEvent(self, event):
        if self._base_min_height:
            self.anim_min.stop()
            self.anim_min.setStartValue(self.minimumHeight())
            self.anim_min.setEndValue(self._base_min_height + self._grow_by)
            self.anim_min.start()
        self.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._base_min_height:
            self.anim_min.stop()
            self.anim_min.setStartValue(self.minimumHeight())
            self.anim_min.setEndValue(self._base_min_height)
            self.anim_min.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ColorActionCard(HoverScaleFrame):
    clicked = pyqtSignal()

    def __init__(self, badge_text, badge_color, title, desc, parent=None):
        super().__init__(parent, grow_by=10)
        self.accent_color = badge_color
        self.setObjectName("ColorActionCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setHoverHeights(150, 10)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        top = QHBoxLayout()
        badge = QLabel(badge_text)
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {badge_color}; color: white; border-radius: 13px; font-size: 18px; font-weight: 900;"
        )
        top.addWidget(badge)
        top.addStretch()
        layout.addLayout(top)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-size: 18px; font-weight: 900; background: transparent;")
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #9FB0C7; font-size: 12px; font-weight: 700; background: transparent;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        layout.addStretch()

        self.apply_card_style(False)

    def apply_card_style(self, hovered=False):
        if hovered:
            self.setStyleSheet(
                f"QFrame#ColorActionCard {{ background-color: {self.accent_color}; border: 1px solid {self.accent_color}; border-radius: 24px; }}"
            )
        else:
            self.setStyleSheet(
                "QFrame#ColorActionCard { background-color: #101A2D; border: 1px solid #26364F; border-radius: 24px; }"
            )

    def enterEvent(self, event):
        self.apply_card_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_card_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ToastLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastLabel")
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)
        self.fade = QPropertyAnimation(self.effect, b"opacity")
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        self.setStyleSheet(
            "QLabel#ToastLabel { background-color: #0B1220; color: #FFFFFF; "
            "border: 1px solid #10B981; border-radius: 18px; "
            "padding: 10px 18px; font-size: 13px; font-weight: 900; }"
        )

    def show_message(self, text, duration=1500):
        self.setText(text)
        self.setMinimumWidth(190)
        self.adjustSize()
        self.setVisible(True)
        self.raise_()
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(1.0)
        self.fade.start()
        self.hide_timer.start(duration)

    def fade_out(self):
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(0.0)
        try:
            self.fade.finished.disconnect(self._hide_after_fade)
        except Exception:
            pass
        self.fade.finished.connect(self._hide_after_fade)
        self.fade.start()

    def _hide_after_fade(self):
        try:
            self.fade.finished.disconnect(self._hide_after_fade)
        except Exception:
            pass
        self.setVisible(False)


class FloatingSettingsButton(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.full_label = label
        self._gear_rotation = 0.0
        self._hovered = False
        self.button_width = 128
        self.button_height = 46
        self._anchor_margin = 24
        self.setObjectName("FloatingSettingsBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(self.button_width, self.button_height)
        self.setMouseTracking(True)

        self.rotation_anim = QPropertyAnimation(self, b"gearRotation")
        self.rotation_anim.setDuration(420)
        self.rotation_anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def gearRotation(self):
        return self._gear_rotation

    @gearRotation.setter
    def gearRotation(self, value):
        self._gear_rotation = value
        self.update()

    def set_anchor_position(self, parent_width, parent_height):
        x = parent_width - self.button_width - self._anchor_margin
        y = parent_height - self.button_height - self._anchor_margin
        self.move(max(0, x), max(0, y))
        self.raise_()

    def enterEvent(self, event):
        self._hovered = True
        self.rotation_anim.stop()
        self.rotation_anim.setStartValue(self._gear_rotation)
        self.rotation_anim.setEndValue(self._gear_rotation + 120.0)
        self.rotation_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.rotation_anim.stop()
        self.rotation_anim.setStartValue(self._gear_rotation)
        self.rotation_anim.setEndValue(0.0)
        self.rotation_anim.start()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)

        bg = QColor("#162238") if self._hovered else QColor("#0F172A")
        border = QColor(self.config.get("accent_color", "#3B82F6")) if self._hovered else QColor("#2A3C59")

        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 23, 23)

        painter.save()
        painter.translate(24, self.height() / 2)
        painter.rotate(self._gear_rotation)
        icon_font = QFont("Segoe UI Symbol", 15, QFont.Bold)
        painter.setFont(icon_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(-10, 8, "⚙")
        painter.restore()

        painter.setPen(QColor("#FFFFFF"))
        txt_font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(txt_font)
        text_rect = rect.adjusted(46, 0, -12, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.full_label)


class ChangelogHoverCard(QFrame):
    def __init__(self, title, hint_text, entries, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.entries = entries
        self.setObjectName("ChangelogHoverCard")
        self.setFixedWidth(360)
        self.setMinimumHeight(210)
        self.setMaximumHeight(210)
        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(280)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("SectionTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_hint = QLabel(hint_text)
        self.lbl_hint.setObjectName("Muted")
        self.lbl_hint.setWordWrap(True)
        layout.addWidget(self.lbl_hint)

        self.lbl_body = QLabel()
        self.lbl_body.setWordWrap(True)
        self.lbl_body.setTextFormat(Qt.RichText)
        self.lbl_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_body.setStyleSheet("color: #E5ECF6; font-size: 13px; line-height: 1.5; background: transparent;")
        # 2.0: Tüm sürüm geçmişi kaydırılarak okunur.
        self.body_scroll = QScrollArea()
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.NoFrame)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body_scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self.body_scroll.setWidget(self.lbl_body)
        layout.addWidget(self.body_scroll, 1)
        self.set_entries(entries)
        self.refresh_style()

    def set_entries(self, entries):
        """entries: [("Sürüm", "Tarih", [maddeler]), ...]  (eski [(tarih, metin)] biçimi de desteklenir)"""
        self.entries = entries
        html_parts = []
        for entry in entries:
            if len(entry) == 3:
                version, date_text, items = entry
                html_parts.append(
                    f'<div style="margin-top:12px; color:#F8FAFC; font-size:14px; font-weight:900;">{html_escape(version)}'
                    f'<span style="color:#A7B8D0; font-size:11px; font-weight:700;">  ·  {html_escape(date_text)}</span></div>'
                )
                for item in items:
                    html_parts.append(f'<div style="margin-top:4px; color:#E5ECF6; font-size:12px;">• {html_escape(item)}</div>')
            else:
                date_text, desc = entry
                html_parts.append(
                    f'<div style="margin-top:8px; color:#A7B8D0; font-size:11px; font-weight:700;">{html_escape(date_text)}</div>'
                    f'<div style="margin-top:4px; color:#F8FAFC; font-size:13px;">• {html_escape(desc)}</div>'
                )
        self.lbl_body.setText("".join(html_parts))

    def refresh_style(self):
        if self._hovered:
            self.setStyleSheet(
                "QFrame#ChangelogHoverCard { background-color: #101A2D; border: 1px solid "
                + str(state.APP_CONFIG.get("accent_color", "#3B82F6")) + "; border-radius: 24px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#ChangelogHoverCard { background-color: #101A2D; border: 1px solid #26364F; border-radius: 24px; }"
            )

    def enterEvent(self, event):
        self._hovered = True
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(self.maximumHeight())
        self.anim.setEndValue(390)
        self.anim.start()
        self.refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.anim.stop()
        self.anim.setStartValue(self.maximumHeight())
        self.anim.setEndValue(210)
        self.anim.start()
        self.refresh_style()
        super().leaveEvent(event)
