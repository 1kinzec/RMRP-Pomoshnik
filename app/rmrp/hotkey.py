"""Глобальная горячая клавиша (Windows, RegisterHotKey). На других ОС — безопасная заглушка."""
import os
import threading

VK = {"F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B, "INSERT": 0x2D, "HOME": 0x24}
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000


class GlobalHotkey:
    def __init__(self, key, callback):
        self.key = key
        self.callback = callback  # вызывается в фоновом потоке — оборачивайте в root.after
        self.available = os.name == "nt" and key in VK
        self.registered = False
        self._tid = None
        self._thread = None
        self._ready = threading.Event()

    def start(self):
        if not self.available or self._thread:
            return False
        self._thread = threading.Thread(target=self._loop, daemon=True, name="hotkey")
        self._thread.start()
        self._ready.wait(2)
        return self.registered

    def _loop(self):
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self._tid = kernel32.GetCurrentThreadId()
        self.registered = bool(user32.RegisterHotKey(None, 1, MOD_NOREPEAT, VK[self.key]))
        self._ready.set()
        if not self.registered:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                try:
                    self.callback()
                except Exception:  # noqa: BLE001
                    pass
        user32.UnregisterHotKey(None, 1)

    def stop(self):
        if self.available and self._tid:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        self._thread = None
        self.registered = False
