"""F24 tuşunu NexStudio'nun send_key_combo'su ile gönderir ve WH_KEYBOARD_LL ile ne geldiğini ölçer."""
import os, sys, ctypes, threading, time
from ctypes import wintypes
os.environ["NEXSTUDIO_DATA_DIR"] = sys.argv[2]
sys.path.insert(0, sys.argv[1])
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _nex
m = _nex.load()  # 2.5.1: kod nexstudio paketinde; tüm modüller tek ad alanında

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
events = []

@HOOKPROC
def proc(n, w, l):
    k = ctypes.cast(l, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
    if k.vkCode == 0x87:
        events.append((w, k.vkCode, k.scanCode, k.flags, time.perf_counter()))
    return user32.CallNextHookEx(None, n, w, l)

def hook_thread():
    h = user32.SetWindowsHookExW(13, proc, None, 0)
    msg = wintypes.MSG()
    end = time.time() + 3
    while time.time() < end:
        if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.001)
    user32.UnhookWindowsHookEx(h)

t = threading.Thread(target=hook_thread); t.start()
time.sleep(0.5)
m.send_key_combo([0x87])  # F24
t.join()
for e in events:
    print("msg=%s vk=0x%X scan=0x%X flags=0x%X" % (hex(e[0]), e[1], e[2], e[3]))
if len(events) >= 2:
    print("basılı kalma: %.0f ms" % ((events[-1][4] - events[0][4]) * 1000))
print("OK" if len(events) >= 2 and all(e[2] != 0 for e in events) else "FAIL")
