"""
Voice-Type Overlay — плавающая пилюля с волной, как Flow Bar у Wispr Flow.

Всё AppKit живёт в главном потоке. Из других потоков дергать только
публичные функции внизу файла — они доставляют вызов через callAfter.
Формула волны и конфигурация панели — по образцу VoiceInk (open source).
"""

import math
import time

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSPanel,
    NSScreen,
    NSStatusWindowLevel,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSObject, NSTimer
from PyObjCTools import AppHelper

PILL_WIDTH, PILL_HEIGHT = 230, 44
BOTTOM_MARGIN = 24

BAR_COUNT, BAR_WIDTH, BAR_GAP = 15, 3.0, 2.0
BAR_MIN, BAR_MAX = 4.0, 28.0

HIDDEN, RECORDING, PROCESSING, DONE, ERROR = range(5)


class WaveView(NSView):
    """Содержимое пилюли: фон + волна/текст в зависимости от состояния."""

    def initWithFrame_(self, frame):
        self = objc.super(WaveView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.state = HIDDEN
        self.level = 0.0  # сглаженный уровень микрофона 0..1
        self.message = ""
        return self

    def drawRect_(self, rect):
        bounds = self.bounds()
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, bounds.size.height / 2, bounds.size.height / 2
        )
        NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.88).set()
        pill.fill()

        if self.state in (RECORDING, PROCESSING):
            self._draw_bars(bounds)
        elif self.state in (DONE, ERROR):
            self._draw_message(bounds)

    def _draw_bars(self, bounds):
        t = time.monotonic()
        total = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        x = (bounds.size.width - total) / 2
        mid_y = bounds.size.height / 2
        center = (BAR_COUNT - 1) / 2

        if self.state == RECORDING:
            NSColor.whiteColor().set()
        else:
            NSColor.colorWithCalibratedWhite_alpha_(0.65, 1.0).set()

        for i in range(BAR_COUNT):
            # буст к центру: крайние столбики ниже, как у VoiceInk
            boost = 1.0 - 0.6 * (abs(i - center) / center)
            if self.state == RECORDING:
                amp = self.level * abs(math.sin(t * 8 + i * 0.5)) * boost
            else:
                # обработка: бегущая волна, микрофон уже не при чём
                amp = (0.5 + 0.5 * math.sin(t * 6 - i * 0.6)) * 0.5 * boost
            h = BAR_MIN + (BAR_MAX - BAR_MIN) * min(amp, 1.0)
            bar = NSMakeRect(x + i * (BAR_WIDTH + BAR_GAP), mid_y - h / 2, BAR_WIDTH, h)
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                bar, BAR_WIDTH / 2, BAR_WIDTH / 2
            ).fill()

    def _draw_message(self, bounds):
        color = (
            NSColor.systemGreenColor() if self.state == DONE else NSColor.systemRedColor()
        )
        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(13),
            NSForegroundColorAttributeName: color,
        }
        text = objc.lookUpClass("NSString").stringWithString_(self.message)
        size = text.sizeWithAttributes_(attrs)
        text.drawAtPoint_withAttributes_(
            (
                (bounds.size.width - size.width) / 2,
                (bounds.size.height - size.height) / 2,
            ),
            attrs,
        )


class _Overlay(NSObject):
    """Владелец панели. Все методы вызывать только на главном потоке."""

    def init(self):
        self = objc.super(_Overlay, self).init()
        if self is None:
            return None

        rect = NSMakeRect(0, 0, PILL_WIDTH, PILL_HEIGHT)
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setLevel_(NSStatusWindowLevel)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setOpaque_(False)
        panel.setHasShadow_(True)
        panel.setIgnoresMouseEvents_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.view = WaveView.alloc().initWithFrame_(rect)
        panel.setContentView_(self.view)
        self.panel = panel
        self.timer = None
        self.hide_timer = None
        return self

    def _position(self):
        screen = NSScreen.mainScreen()
        if screen is None:
            return
        vf = screen.visibleFrame()
        x = vf.origin.x + (vf.size.width - PILL_WIDTH) / 2
        y = vf.origin.y + BOTTOM_MARGIN
        self.panel.setFrameOrigin_((x, y))

    def _show(self):
        self._position()
        self._cancel_hide()
        if self.timer is None:
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1 / 30.0, self, "tick:", None, True
            )
        self.panel.orderFrontRegardless()

    def _cancel_hide(self):
        if self.hide_timer is not None:
            self.hide_timer.invalidate()
            self.hide_timer = None

    def tick_(self, _timer):
        self.view.setNeedsDisplay_(True)

    def setState_message_(self, state, message):
        self.view.state = state
        self.view.message = message
        if state == HIDDEN:
            self.hidePanel_(None)
            return
        self._show()
        if state in (DONE, ERROR):
            self._cancel_hide()
            delay = 1.5 if state == DONE else 2.5
            self.hide_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                delay, self, "hidePanel:", None, False
            )

    def setLevel_(self, value):
        self.view.level = value

    def hidePanel_(self, _timer):
        self._cancel_hide()
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        self.view.state = HIDDEN
        self.panel.orderOut_(None)


_overlay = None


def setup_app():
    """Вызвать один раз из главного потока до run_forever()."""
    global _overlay
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    _overlay = _Overlay.alloc().init()


def run_forever():
    """Отдаёт главный поток событийному циклу AppKit. Не возвращается."""
    AppHelper.runEventLoop()


# --- Потокобезопасный API (можно звать из pynput/pyaudio/сетевых потоков) ---

def _set(state, message=""):
    AppHelper.callAfter(_overlay.setState_message_, state, message)


def show_recording():
    _set(RECORDING)


def set_level(value):
    AppHelper.callAfter(_overlay.setLevel_, max(0.0, min(1.0, value)))


def show_processing():
    _set(PROCESSING)


def show_done(text="✓  Cmd+V"):
    _set(DONE, text)


def show_error(text="Ошибка"):
    _set(ERROR, text)


def hide():
    _set(HIDDEN)
