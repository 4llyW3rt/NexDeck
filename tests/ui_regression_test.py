"""
NexStudio automated UI regression test (headless browser via CDP, stdlib only).

Starts an isolated NexStudio core with NEXSTUDIO_DATA_DIR inside agy_work/ui/data,
drives installed Microsoft Edge (or Chrome) headless over Chrome DevTools Protocol
using only Python's standard library (checks for playwright first; falls back to
Edge CDP without downloading browsers or installing packages).

Safety guarantees:
- Isolated data dir inside agy_work/ui/data; never touches %APPDATA%\\NexStudio.
- auto_connect=False, welcome_done=True; never connects to COM12 or calls set_app_mode("device").
- Never touches ports 56403, 55353, or 45729; immediately stops the mobile server if
  switching to web mode auto-starts it.
- Never calls /api2/volume, never rotates knobs/wheels, never clicks/presses keys,
  never sets start_with_win, never installs updates.
- Always terminates browser and core processes in a finally block.

Usage:
    python "C:/Users/alime/Desktop/NexHub Cop/agy_work/ui/ui_regression_test.py"
"""
import base64
import importlib.util
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import traceback
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "src")
DATA_DIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(SCRIPT_DIR, "data")

FORBIDDEN_PORTS = {56403, 55353, 45729}
VIEWPORTS = [(1400, 860), (1100, 700), (700, 900), (375, 812)]
BROWSERS = [
    os.environ.get("NEX_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

results = []  # list of (passed: bool, name: str, detail: str)
warns = []

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append((ok, name, detail))
    suffix = f"  [{detail}]" if (not ok and detail) else ""
    print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}", flush=True)
    return ok


def pick_free_port():
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            if port not in FORBIDDEN_PORTS:
                return port
    raise RuntimeError("Could not allocate a free local port")


# ---------------- Minimal RFC 6455 WebSocket + CDP client ----------------
class WS:
    def __init__(self, url, timeout=30.0):
        assert url.startswith("ws://"), f"Unexpected ws url: {url}"
        host, rest = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)), timeout=timeout)
        self.s.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET /{rest} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.s.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.s.recv(1)
            if not chunk:
                raise ConnectionError("WebSocket handshake closed")
            buf += chunk
        status_line = buf.split(b"\r\n", 1)[0]
        assert b" 101 " in status_line, f"WS upgrade failed: {status_line!r}"

    def _send_frame(self, opcode, payload):
        hdr = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        self.s.sendall(hdr + mask + masked)

    def send(self, text):
        self._send_frame(0x1, text.encode("utf-8"))

    def _read_exact(self, n, allow_initial_timeout=False):
        out = b""
        while len(out) < n:
            try:
                chunk = self.s.recv(n - len(out))
            except socket.timeout:
                if allow_initial_timeout and not out:
                    raise
                # Once we started reading a frame, finish it so the stream never desyncs.
                self.s.settimeout(30.0)
                continue
            if not chunk:
                raise ConnectionError("WebSocket closed")
            out += chunk
            if allow_initial_timeout and len(out) < n:
                self.s.settimeout(30.0)
        return out

    def recv(self, allow_timeout=False):
        data = bytearray()
        msg_op = None
        while True:
            b1, b2 = self._read_exact(2, allow_initial_timeout=(allow_timeout and msg_op is None))
            fin = bool(b1 & 0x80)
            op = b1 & 0x0F
            masked = bool(b2 & 0x80)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(n) if n else b""
            if mask:
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))

            if op == 0x8:  # close
                raise ConnectionError("WebSocket closed by peer")
            if op == 0x9:  # ping -> pong
                self._send_frame(0xA, payload)
                continue
            if op == 0xA:  # pong
                continue
            if op in (0x1, 0x2):
                msg_op = op
                data.extend(payload)
            elif op == 0x0:
                data.extend(payload)
            if fin and msg_op in (0x1, 0x2):
                return data.decode("utf-8", "replace")

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.seq = 0
        self.errors = []
        self.load_count = 0

    def call(self, method, **params):
        self.seq += 1
        mid = self.seq
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} error: {msg['error']}")
                return msg.get("result", {})
            self._handle_event(msg)

    def _handle_event(self, msg):
        meth = msg.get("method")
        p = msg.get("params", {})
        if meth == "Page.loadEventFired":
            self.load_count += 1
        elif meth == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            desc = (d.get("exception", {}).get("description") or d.get("text", "")).splitlines()[0]
            loc = f"@{d.get('lineNumber', '?')}:{d.get('columnNumber', '?')}"
            self.errors.append(f"exception{loc}: {desc}")
        elif meth == "Runtime.consoleAPICalled" and p.get("type") == "error":
            parts = [str(a.get("value", a.get("description", ""))) for a in p.get("args", [])]
            self.errors.append("console.error: " + " ".join(parts)[:240])
        elif meth == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
            e = p["entry"]
            if "favicon" not in e.get("url", ""):
                self.errors.append(f"log: {e.get('text', '')} {e.get('url', '')}".strip())

    def pump(self, secs):
        end = time.monotonic() + secs
        while True:
            rem = end - time.monotonic()
            if rem <= 0:
                break
            self.ws.s.settimeout(min(0.15, rem))
            try:
                raw = self.ws.recv(allow_timeout=True)
                self._handle_event(json.loads(raw))
            except socket.timeout:
                pass
        self.ws.s.settimeout(30.0)

    def ev(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError("eval exception: " + json.dumps(r["exceptionDetails"])[:300] + " :: " + expr[:140])
        return r.get("result", {}).get("value")


def pause(c, secs=0.35):
    c.pump(secs)


# ---------------- Browser/DOM helpers ----------------
JS_TOPMOST = r"""((sel, pts, checkTop60) => {
  const el = document.querySelector(sel);
  if (!el) return { ok: false, why: 'missing' };
  const r = el.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return { ok: false, why: 'zero-size', rect: [r.left, r.top, r.width, r.height].map(Math.round) };
  const inViewport = r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1;
  const bad = [];
  let n = 0;
  const padX = Math.min(10, Math.max(2, r.width / 8));
  const padY = Math.min(10, Math.max(2, r.height / 8));
  for (let i = 0; i <= pts; i++) {
    for (let j = 0; j <= pts; j++) {
      const x = r.left + padX + (r.width - 2 * padX) * i / pts;
      const y = r.top + padY + (r.height - 2 * padY) * j / pts;
      if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) continue;
      n++;
      const t = document.elementFromPoint(x, y);
      if (!t || !el.contains(t)) {
        bad.push(Math.round(x) + ',' + Math.round(y) + ':' + (t ? (t.id || t.className || t.tagName) : 'null'));
      }
    }
  }
  const topBad = [];
  if (checkTop60) {
    const xs = [r.left + padX, r.left + r.width / 2, r.right - padX];
    for (let y = r.top + 2; y < Math.min(r.top + 60, r.bottom - 1, innerHeight); y += 6) {
      for (const x of xs) {
        if (x < 0 || x >= innerWidth || y < 0) continue;
        const t = document.elementFromPoint(x, y);
        if (!t || !el.contains(t)) {
          topBad.push(Math.round(x) + ',' + Math.round(y) + ':' + (t ? (t.id || t.className || t.tagName) : 'null'));
        }
      }
    }
  }
  return {
    ok: n > 0 && bad.length === 0 && topBad.length === 0,
    inViewport,
    n,
    bad: bad.slice(0, 5),
    topBad: topBad.slice(0, 5),
    rect: [r.left, r.top, r.width, r.height].map(Math.round),
    vw: innerWidth,
    vh: innerHeight,
  };
})"""


def topmost(c, sel, pts=6, check_top60=False):
    return c.ev(f"({JS_TOPMOST})({json.dumps(sel)}, {pts}, {'true' if check_top60 else 'false'})")


def is_vis(c, sel):
    return bool(c.ev(
        f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return false; "
        f"const s = getComputedStyle(e); const r = e.getBoundingClientRect(); "
        f"return !e.hidden && s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; }})()"
    ))


def is_drawer_open(c):
    return bool(c.ev("document.querySelector('#drawer')?.classList.contains('open')"))


def send_key(c, key_name, code=None):
    code = code or key_name
    c.call("Input.dispatchKeyEvent", type="keyDown", key=key_name, code=code)
    c.call("Input.dispatchKeyEvent", type="keyUp", key=key_name, code=code)
    pause(c, 0.25)


def js_click(c, sel, wait=0.35):
    ok = c.ev(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return false; e.click(); return true; }})()")
    if not ok:
        raise RuntimeError(f"Element not found for click: {sel}")
    pause(c, wait)


def view_all(c):
    c.ev("document.querySelector('#view-all')?.click(); 0")
    pause(c, 0.25)


def reset_ui(c):
    send_key(c, "Escape")
    c.ev("localStorage.removeItem('nex-view'); 0")
    view_all(c)
    c.ev("document.querySelector('#drawer')?.classList.remove('open'); 0")
    c.ev("if (!document.querySelector('#modal').hidden) document.querySelector('#modal-cancel')?.click(); 0")
    pause(c, 0.25)


def open_view_menu_clean(c):
    """Opens #view-menu via #view-btn on >760px, or via hiding topbar + #restore on <=760px."""
    if is_vis(c, "#view-btn"):
        js_click(c, "#view-btn", 0.35)
    else:
        # On <=760px, .viewwrap is display:none by design; enable #restore via top part toggle
        if not is_vis(c, "#restore"):
            c.ev("document.querySelector('[data-part=top]').click(); 0")
            pause(c, 0.25)
        js_click(c, "#restore", 0.35)


def navigate_viewport(c, w, h, url, clear_view=True):
    c.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
    before = c.load_count
    c.call("Page.navigate", url=url)
    for _ in range(60):
        c.pump(0.15)
        if c.load_count > before:
            break
    for _ in range(50):
        ready = c.ev(
            "document.readyState === 'complete' && !!document.querySelector('#view-btn') "
            "&& typeof S !== 'undefined' && S !== null"
        )
        if ready:
            break
        pause(c, 0.2)
    if clear_view:
        c.ev("localStorage.removeItem('nex-view'); 0")
        view_all(c)
    pause(c, 0.3)


# ---------------- Test sections ----------------
def test_stacking(c, tag):
    # 1a. #view-menu topmost and inside viewport
    open_view_menu_clean(c)
    r = topmost(c, "#view-menu", pts=6, check_top60=True)
    check(f"{tag} stacking: #view-menu topmost & in viewport", r["ok"] and r["inViewport"] and is_vis(c, "#view-menu"), json.dumps(r))
    send_key(c, "Escape")
    view_all(c)

    # 1b. #drawer topmost (including top 60px)
    js_click(c, "#open-changelog", 0.35)
    for _ in range(15):
        st = c.ev("(() => { const d = document.querySelector('#drawer'); return { t: getComputedStyle(d).transform, r: Math.round(d.getBoundingClientRect().right) }; })()")
        if st["t"] == "none" or st["r"] <= c.ev("innerWidth") + 1:
            break
        pause(c, 0.12)
    r = topmost(c, "#drawer", pts=6, check_top60=True)
    d_open = is_drawer_open(c)
    if not (r["ok"] and d_open):
        r["drawerOpen"] = d_open
        r["drawerCls"] = c.ev("document.querySelector('#drawer')?.className")
        r["drawerTransform"] = c.ev("getComputedStyle(document.querySelector('#drawer')).transform")
        r["perfNow"] = c.ev("Math.round(performance.now())")
    check(f"{tag} stacking: #drawer topmost (incl. top 60px)", r["ok"] and d_open, json.dumps(r))
    send_key(c, "Escape")
    pause(c, 0.35)

    # 1c. dialog() modal topmost & OK button inside viewport with long text
    c.ev("window.__testDialog = window.dialog({title: 'Long Dialog Title', text: 'Long dialog regression text line. '.repeat(200)}); 0")
    pause(c, 0.4)
    rm = topmost(c, "#modal .box", pts=6, check_top60=True)
    check(f"{tag} stacking: dialog() modal box topmost & in viewport", rm["ok"] and rm["inViewport"] and is_vis(c, "#modal"), json.dumps(rm))
    rok = c.ev("""(() => {
      const b = document.querySelector('#modal-ok');
      if (!b) return { ok: false, why: 'no #modal-ok' };
      const r = b.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const within = r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
      const t = (cx >= 0 && cy >= 0 && cx < innerWidth && cy < innerHeight) ? document.elementFromPoint(cx, cy) : null;
      return {
        ok: within && !!t && (t === b || b.contains(t)),
        within,
        top: t ? (t.id || t.className || t.tagName) : null,
        rect: [r.left, r.top, r.right, r.bottom].map(Math.round),
        vw: innerWidth,
        vh: innerHeight,
      };
    })()""")
    check(f"{tag} stacking: dialog() OK button inside viewport & topmost", rok["ok"], json.dumps(rok))
    js_click(c, "#modal-ok", 0.25)
    check(f"{tag} stacking: dialog() closes on OK", not is_vis(c, "#modal"))


def test_exclusion(c, tag):
    # Ensure trigger for view menu is ready (for <=760px, make #restore visible first so we never click anything between drawer & menu)
    if not is_vis(c, "#view-btn"):
        c.ev("document.querySelector('[data-part=top]').click(); 0")
        pause(c, 0.25)
        if is_vis(c, "#view-menu"):
            send_key(c, "Escape")
    trigger = "#view-btn" if is_vis(c, "#view-btn") else "#restore"

    # Open view-menu, then open drawer -> view-menu must close
    js_click(c, trigger, 0.35)
    menu_was_open = is_vis(c, "#view-menu")
    js_click(c, "#open-changelog", 0.55)
    check(
        f"{tag} exclusion: opening #drawer closes #view-menu",
        menu_was_open and is_drawer_open(c) and not is_vis(c, "#view-menu"),
        f"menu_was_open={menu_was_open} drawer={is_drawer_open(c)} menu={is_vis(c, '#view-menu')}",
    )

    # With drawer open, open view-menu -> drawer must close
    drawer_was_open = is_drawer_open(c)
    js_click(c, trigger, 0.45)
    check(
        f"{tag} exclusion: opening #view-menu closes #drawer",
        drawer_was_open and is_vis(c, "#view-menu") and not is_drawer_open(c),
        f"drawer_was_open={drawer_was_open} menu={is_vis(c, '#view-menu')} drawer={is_drawer_open(c)}",
    )

    # Escape closes #view-menu
    send_key(c, "Escape")
    check(f"{tag} exclusion: Escape closes #view-menu", not is_vis(c, "#view-menu") and not is_drawer_open(c))

    # Open #drawer, Escape closes #drawer
    js_click(c, "#open-changelog", 0.5)
    opened_again = is_drawer_open(c)
    send_key(c, "Escape")
    check(
        f"{tag} exclusion: Escape closes #drawer",
        opened_again and not is_drawer_open(c) and not is_vis(c, "#view-menu"),
        f"opened_again={opened_again} drawer={is_drawer_open(c)} menu={is_vis(c, '#view-menu')}",
    )


def test_focus_mode(c, tag, width):
    view_all(c)
    has_view_btn = is_vis(c, "#view-btn")

    # Test each [data-part] toggle
    for part in ("rail", "top", "lib", "insp"):
        if has_view_btn:
            js_click(c, "#view-btn", 0.25)
        js_click(c, f"[data-part={part}]", 0.25)
        has_cls = bool(c.ev(f"document.body.classList.contains('hide-{part}')"))
        aria_off = c.ev(f"document.querySelector('[data-part={part}').getAttribute('aria-checked')") == "false"
        check(f"{tag} focus: [data-part={part}] hides part", has_cls and aria_off, f"cls={has_cls} aria_off={aria_off}")

        if part == "top":
            # Close menu if open, verify #restore is visible and opens #view-menu topmost
            if is_vis(c, "#view-menu"):
                send_key(c, "Escape")
            rest_vis = is_vis(c, "#restore")
            check(f"{tag} focus: #restore visible when topbar hidden", rest_vis)
            js_click(c, "#restore", 0.35)
            rm = topmost(c, "#view-menu", pts=6, check_top60=True)
            check(
                f"{tag} focus: #restore opens #view-menu topmost when topbar hidden",
                is_vis(c, "#view-menu") and rm["ok"] and rm["inViewport"],
                json.dumps(rm),
            )

        if part == "rail" and width <= 700:
            h = c.ev("Math.round(document.querySelector('.rail').getBoundingClientRect().height * 10) / 10")
            check(f"{tag} focus: hidden .rail height < 120px at {width}px", h < 120, f"height={h}")

        view_all(c)

    # Test full focus mode via [data-focus] and restore via #restore -> #view-all
    if has_view_btn:
        js_click(c, "#view-btn", 0.25)
    js_click(c, "[data-focus]", 0.3)
    all_hidden = bool(c.ev("['rail','top','lib','insp'].every(p => document.body.classList.contains('hide-'+p))"))
    if is_vis(c, "#view-menu"):
        send_key(c, "Escape")
    js_click(c, "#restore", 0.3)
    menu_open_in_focus = is_vis(c, "#view-menu")
    js_click(c, "#view-all", 0.3)
    all_restored = bool(c.ev("['rail','top','lib','insp'].every(p => !document.body.classList.contains('hide-'+p))"))
    restore_hidden = not is_vis(c, "#restore")
    check(
        f"{tag} focus: [data-focus] hides all, #restore + #view-all restores all",
        all_hidden and menu_open_in_focus and all_restored and restore_hidden,
        f"all_hidden={all_hidden} menu={menu_open_in_focus} restored={all_restored} restore_hidden={restore_hidden}",
    )

    # Also test F11 toggles focus mode
    send_key(c, "F11", "F11")
    f11_on = bool(c.ev("['rail','top','lib','insp'].every(p => document.body.classList.contains('hide-'+p))"))
    send_key(c, "F11", "F11")
    f11_off = bool(c.ev("['rail','top','lib','insp'].every(p => !document.body.classList.contains('hide-'+p))"))
    check(f"{tag} focus: F11 toggles focus mode on/off", f11_on and f11_off, f"on={f11_on} off={f11_off}")


def test_overflow(c, tag, pages, expect_free_grid=False):
    for pg in pages:
        view_all(c)
        exists = bool(c.ev(f"(() => {{ const b = document.querySelector('.rail [data-page={pg}]'); return !!b && !b.hidden; }})()"))
        if not exists:
            check(f"{tag} overflow: nav button '{pg}' present", False)
            continue
        js_click(c, f".rail [data-page={pg}]", 0.45)
        r = c.ev("""(() => {
          const iw = innerWidth;
          const sw = document.documentElement.scrollWidth;
          const bw = document.body.scrollWidth;
          let worst = null;
          // Check both document scrollWidth and major content containers (in case overflow-x:hidden masks clipping)
          const page = document.querySelector('.page.active');
          if (page) {
            for (const sel of ['.deck', '.screen', '#slots', '.settings', '.topbar', '.library', '.inspector']) {
              const el = page.querySelector(sel) || document.querySelector(sel);
              if (!el) continue;
              const s = getComputedStyle(el);
              if (s.display === 'none' || s.visibility === 'hidden') continue;
              const rc = el.getBoundingClientRect();
              if (rc.width > 0 && rc.height > 0 && (rc.right > iw + 1 || rc.left < -1)) {
                if (!worst || rc.right > worst.right) {
                  worst = { sel, left: Math.round(rc.left), right: Math.round(rc.right), width: Math.round(rc.width) };
                }
              }
            }
          }
          if (!worst && (sw > iw + 1 || bw > iw + 1)) {
            for (const el of document.querySelectorAll('body *')) {
              const s = getComputedStyle(el);
              if (s.display === 'none' || s.visibility === 'hidden') continue;
              if (el.closest('#drawer:not(.open), .screen-tabs')) continue;
              const rc = el.getBoundingClientRect();
              if (rc.width > 0 && rc.height > 0 && rc.right > iw + 1) {
                if (!worst || rc.right > worst.right) {
                  worst = { tag: el.tagName.toLowerCase(), id: el.id, cls: String(el.className).slice(0, 40), right: Math.round(rc.right), width: Math.round(rc.width) };
                }
              }
            }
          }
          return { sw, bw, iw, worst };
        })()""")
        check(
            f"{tag} overflow: '{pg}' page has no horizontal overflow",
            r["sw"] <= r["iw"] + 1 and r["bw"] <= r["iw"] + 1 and r["worst"] is None,
            json.dumps(r),
        )
        if expect_free_grid and pg == "device":
            g = c.ev("({slots: document.querySelectorAll('#slots .slot').length, tabs: document.querySelectorAll('#screen-tabs button').length, free: document.querySelector('.screen')?.classList.contains('free')})")
            check(f"{tag} free-grid 6x4x8 rendered (24 slots, 8 tabs)", g["free"] and g["slots"] == 24 and g["tabs"] == 8, json.dumps(g))


def test_extra_wheel_dialog(c, tag):
    view_all(c)
    js_click(c, ".rail [data-page=device]", 0.4)
    has_btn = bool(c.ev("!!document.querySelector('.wheel.add button')"))
    check(f"{tag} extra-wheel: add button present", has_btn)
    if not has_btn:
        return
    js_click(c, ".wheel.add button", 0.9)
    info = c.ev("""(() => {
      const m = document.querySelector('#modal');
      const s = document.querySelector('#modal-select');
      const visible = !!m && !m.hidden && !!s && !s.hidden;
      const opts = s ? [...s.options].map(o => ({v: o.value, l: o.textContent.trim()})) : [];
      return { visible, count: opts.length, sample: opts.slice(0, 5) };
    })()""")
    check(
        f"{tag} extra-wheel: dialog opens with options",
        info["visible"] and info["count"] > 0,
        json.dumps(info),
    )
    js_click(c, "#modal-cancel", 0.25)
    check(f"{tag} extra-wheel: cancel closes dialog", not is_vis(c, "#modal"))


def scan_turkish_leftovers(c):
    return c.ev(r"""(() => {
      const out = [];
      const re = /[ğşıİŞĞ]/;
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) {
        const n = w.currentNode;
        const t = n.textContent.trim();
        if (!t || !re.test(t)) continue;
        const p = n.parentElement;
        if (!p || p.closest('[data-no-i18n],script,style,template,textarea,[hidden]')) continue;
        const s = getComputedStyle(p);
        if (s.display === 'none' || s.visibility === 'hidden' || !p.getClientRects().length) continue;
        const label = p.id ? '#' + p.id : p.tagName.toLowerCase() + (p.className ? '.' + String(p.className).trim().split(/\s+/)[0] : '');
        out.push(label + ': ' + t.slice(0, 60));
      }
      // Also check visible attributes translated by I18N_ATTRS
      for (const el of document.querySelectorAll('[placeholder],[title],[aria-label]')) {
        if (el.closest('[data-no-i18n],script,style,template,textarea,[hidden]')) continue;
        const s = getComputedStyle(el);
        if (s.display === 'none' || s.visibility === 'hidden' || !el.getClientRects().length) continue;
        for (const attr of ['placeholder', 'title', 'aria-label']) {
          const v = el.getAttribute(attr);
          if (v && re.test(v)) {
            const label = el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().split(/\s+/)[0] : '');
            out.push(`${label}[${attr}]: ${v.slice(0, 60)}`);
          }
        }
      }
      return out;
    })()""")


def test_i18n(c, url, api):
    def switch_and_reload(lang):
        api("settings", {"key": "language", "value": lang})
        navigate_viewport(c, 1400, 860, url)
        pause(c, 0.8)

    rail_js = "[...document.querySelectorAll('.rail button')].filter(b => !b.hidden).map(b => b.textContent.trim()).join('|')"

    # --- EN ---
    switch_and_reload("en")
    rail = c.ev(rail_js)
    check("i18n en: rail contains 'Device' and 'Settings'", "Device" in rail and "Settings" in rail, rail)
    aria1 = c.ev("document.querySelector('.key[data-sig=\"BTN:1\"]')?.getAttribute('aria-label') || ''")
    check("i18n en: key 1 aria-label is 'Key 1: empty'", aria1 == "Key 1: empty", f"got={aria1!r}")
    for pg in ("device", "web", "settings"):
        js_click(c, f".rail [data-page={pg}]", 0.45)
        if pg == "settings":
            c.ev("const d = document.querySelector('details.adv'); if (d) d.open = true; 0")
            pause(c, 0.2)
        off = scan_turkish_leftovers(c)
        if off:
            warns.append(f"en/{pg}: " + " || ".join(off[:15]))
    # Check #view-menu and #drawer in EN too
    js_click(c, "#view-btn", 0.3)
    off = scan_turkish_leftovers(c)
    if off:
        warns.append("en/view-menu: " + " || ".join(off[:10]))
    send_key(c, "Escape")
    js_click(c, "#open-changelog", 0.5)
    off = scan_turkish_leftovers(c)
    if off:
        warns.append("en/drawer: " + " || ".join(off[:10]))
    send_key(c, "Escape")
    js_click(c, ".rail [data-page=device]", 0.35)
    if c.ev("!!document.querySelector('.wheel.add button')"):
        js_click(c, ".wheel.add button", 0.8)
        off = scan_turkish_leftovers(c)
        if off:
            warns.append("en/wheel-modal: " + " || ".join(off[:10]))
        js_click(c, "#modal-cancel", 0.25)

    # --- DE ---
    switch_and_reload("de")
    rail = c.ev(rail_js)
    check("i18n de: rail translated from Turkish (no 'Ayarlar')", "Ayarlar" not in rail and "Gerät" in rail and "Einstellungen" in rail, rail)
    aria1_de = c.ev("document.querySelector('.key[data-sig=\"BTN:1\"]')?.getAttribute('aria-label') || ''")
    check("i18n de: key 1 aria-label translated from Turkish", "Tuş" not in aria1_de and "boş" not in aria1_de and bool(aria1_de), f"got={aria1_de!r}")
    for pg in ("device", "web", "settings"):
        js_click(c, f".rail [data-page={pg}]", 0.45)
        if pg == "settings":
            c.ev("const d = document.querySelector('details.adv'); if (d) d.open = true; 0")
            pause(c, 0.2)
        off = scan_turkish_leftovers(c)
        if off:
            warns.append(f"de/{pg}: " + " || ".join(off[:15]))
    js_click(c, "#open-changelog", 0.5)
    off = scan_turkish_leftovers(c)
    if off:
        warns.append("de/drawer: " + " || ".join(off[:10]))
    send_key(c, "Escape")
    js_click(c, ".rail [data-page=device]", 0.35)
    if c.ev("!!document.querySelector('.wheel.add button')"):
        js_click(c, ".wheel.add button", 0.8)
        off = scan_turkish_leftovers(c)
        if off:
            warns.append("de/wheel-modal: " + " || ".join(off[:10]))
        js_click(c, "#modal-cancel", 0.25)

    # --- TR ---
    switch_and_reload("tr")
    rail = c.ev(rail_js)
    check("i18n tr: Turkish restored ('Cihaz' and 'Ayarlar')", "Cihaz" in rail and "Ayarlar" in rail, rail)
    aria1_tr = c.ev("document.querySelector('.key[data-sig=\"BTN:1\"]')?.getAttribute('aria-label') || ''")
    check("i18n tr: key 1 aria-label is 'Tuş 1: boş'", aria1_tr == "Tuş 1: boş", f"got={aria1_tr!r}")

    # --- Live switch in UI (#lang-select tr -> en -> de -> tr) ---
    js_click(c, ".rail [data-page=settings]", 0.4)
    c.ev("(() => { const s = document.querySelector('#lang-select'); s.value = 'en'; s.dispatchEvent(new Event('change')); })()")
    pause(c, 1.0)
    js_click(c, ".rail [data-page=device]", 0.4)
    live_aria = c.ev("document.querySelector('.key[data-sig=\"BTN:1\"]')?.getAttribute('aria-label') || ''")
    check("i18n live tr->en: key 1 aria-label becomes 'Key 1: empty'", live_aria == "Key 1: empty", f"got={live_aria!r}")
    # Restore tr cleanly
    api("settings", {"key": "language", "value": "tr"})
    navigate_viewport(c, 1400, 860, url)


def main():
    t0 = time.time()
    has_pw = importlib.util.find_spec("playwright") is not None
    print(f"INFO playwright installed: {has_pw}", flush=True)

    browser = next((b for b in BROWSERS if b and os.path.exists(b)), None)
    if not browser:
        print("FAIL No Edge/Chrome executable found (set NEX_BROWSER)", flush=True)
        return 1
    print(f"INFO browser: {browser} (CDP stdlib driver)", flush=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    for f in ("runtime.json", "config.json", "config.json.bak"):
        try:
            os.remove(os.path.join(DATA_DIR, f))
        except FileNotFoundError:
            pass

    init_cfg = {
        "ui_mode": "classic",
        "app_mode": "device",
        "auto_connect": False,
        "welcome_done": True,
        "web_auto_start": False,
        "web_access_mode": "pin",
        "language": "tr",
    }
    with open(os.path.join(DATA_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(init_cfg, f)

    env = dict(
        os.environ,
        NEXSTUDIO_DATA_DIR=DATA_DIR,
        QT_QPA_PLATFORM="offscreen",
        PYTHONIOENCODING="utf-8",
    )
    core = subprocess.Popen(
        [sys.executable, os.path.join(SRC_DIR, "nexstudio_ui.py")],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    prof_dir = os.path.join(SCRIPT_DIR, f"edge_profile_{os.getpid()}")
    shutil.rmtree(prof_dir, ignore_errors=True)
    os.makedirs(prof_dir, exist_ok=True)
    br = None
    ws = None

    try:
        rt_path = os.path.join(DATA_DIR, "runtime.json")
        for _ in range(80):
            if os.path.exists(rt_path):
                try:
                    with open(rt_path, "r", encoding="utf-8") as f:
                        rt = json.load(f)
                    if rt.get("port") and rt.get("token"):
                        break
                except Exception:
                    pass
            time.sleep(0.25)
        else:
            raise RuntimeError("Core did not write runtime.json in time")

        port = int(rt["port"])
        token = rt["token"]
        assert port not in FORBIDDEN_PORTS, f"Refusing forbidden port {port}"
        base = f"http://127.0.0.1:{port}"
        print(f"INFO isolated core on 127.0.0.1:{port}", flush=True)

        def api(ep, body=None):
            data = None if body is None else json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                f"{base}/api2/{ep}",
                data=data,
                headers={"X-Nex-Token": token, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

        dbg_port = pick_free_port()
        br_log_path = os.path.join(SCRIPT_DIR, f"edge_stderr_{os.getpid()}.log")
        br_log_f = open(br_log_path, "wb")
        br = subprocess.Popen(
            [
                browser,
                "--headless=new",
                f"--remote-debugging-port={dbg_port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={prof_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-gpu",
                "--mute-audio",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-features=CalculateNativeWinOcclusion",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=br_log_f,
        )

        tab = None
        last_cdp_err = None
        for _ in range(60):
            if br.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{dbg_port}/json", timeout=2) as r:
                    tabs = json.loads(r.read().decode("utf-8"))
                tab = next((t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
                if tab:
                    break
            except Exception as exc:
                last_cdp_err = exc
                time.sleep(0.25)
        br_log_f.close()
        if not tab:
            stderr_txt = ""
            try:
                with open(br_log_path, "r", encoding="utf-8", errors="replace") as f:
                    stderr_txt = f.read()[-1500:]
            except Exception:
                pass
            raise RuntimeError(
                f"Headless browser CDP endpoint did not become ready (rc={br.poll()}, err={last_cdp_err!r}, stderr={stderr_txt!r})"
            )

        ws = WS(tab["webSocketDebuggerUrl"])
        c = CDP(ws)
        for domain in ("Page", "Runtime", "Log"):
            c.call(domain + ".enable")
        c.call("Page.bringToFront")
        c.call("Emulation.setFocusEmulationEnabled", enabled=True)

        url = f"{base}/app?t={token}"

        # ---- Phase 1: Device mode (already 'device' in config.json; never call set_app_mode("device")) ----
        for w, h in VIEWPORTS:
            tag = f"[{w}x{h}]"
            navigate_viewport(c, w, h, url)
            test_stacking(c, tag)
            reset_ui(c)
            test_exclusion(c, tag)
            reset_ui(c)
            test_focus_mode(c, tag, w)
            reset_ui(c)
            test_overflow(c, f"{tag} device", ("device", "web", "settings"))
            test_extra_wheel_dialog(c, tag)

        # ---- Phase 2: i18n (while still in device mode so #keys is visible for 'Key 1: empty') ----
        test_i18n(c, url, api)

        # ---- Phase 3: Web mode with free grid 6x4x8 ----
        api("settings", {"key": "web_layout", "value": "grid"})
        api("settings", {"key": "web_grid", "value": {"cols": 6, "rows": 4, "pages": 8}})
        api("settings", {"key": "app_mode", "value": "web"})
        # Safety: if switching to web mode auto-started the mobile web server, stop it immediately
        # so we never occupy port 45729.
        time.sleep(0.5)
        web_info = api("web")
        if web_info.get("running"):
            web_url = web_info.get("url", "")
            print(f"INFO stopping auto-started mobile web server ({web_url})", flush=True)
            api("web", {"op": "stop"})

        for w, h in VIEWPORTS:
            tag = f"[{w}x{h}] web-6x4x8"
            navigate_viewport(c, w, h, url)
            test_overflow(c, tag, ("device", "web", "settings"), expect_free_grid=True)

        c.pump(0.5)
        errs = sorted(set(c.errors))
        check("JS exceptions/errors: none", len(errs) == 0, " | ".join(errs[:8]))

    except Exception as exc:
        traceback.print_exc()
        check(f"unhandled test runner exception: {exc}", False)
    finally:
        if ws:
            ws.close()
        for proc in (br, core):
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except Exception:
                        pass
        shutil.rmtree(prof_dir, ignore_errors=True)
        try:
            os.remove(os.path.join(SCRIPT_DIR, f"edge_stderr_{os.getpid()}.log"))
        except OSError:
            pass

    for w in warns:
        print("WARN leftover Turkish letters: " + w, flush=True)

    passed = sum(1 for ok, _, _ in results if ok)
    failed = sum(1 for ok, _, _ in results if not ok)
    print(f"\nSUMMARY: {passed} PASS, {failed} FAIL, {len(warns)} WARN ({time.time() - t0:.1f}s)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
