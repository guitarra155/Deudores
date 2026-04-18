import os
import time
import ctypes
import threading

def init_watchdog():
    def _watchdog():
        time.sleep(3)
        found_once = False
        while True:
            hwnd = ctypes.windll.user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", None)
            if hwnd != 0:
                found_once = True
            elif found_once:
                os._exit(0)
            time.sleep(1)
    threading.Thread(target=_watchdog, daemon=True).start()
