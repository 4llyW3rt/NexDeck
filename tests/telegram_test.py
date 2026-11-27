"""
NexStudio 2.8.1 Telegram bridge isolated test suite (mock Telegram Bot API).
Uses a local mock Telegram Bot API; never contacts api.telegram.org.
"""
import http.server
import json
import os
import shutil
import socketserver
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import tempfile
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
# Kullanım: python tests/telegram_test.py [src klasörü] [geçici veri klasörü]
SRC_DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO_ROOT / "src"
DATA_DIR = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(tempfile.gettempdir()) / "nexstudio_telegram_test"

# Clean isolated data dir before importing nexstudio (core.py reads NEXSTUDIO_DATA_DIR at import time)
if DATA_DIR.exists():
    shutil.rmtree(DATA_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)

os.environ["NEXSTUDIO_DATA_DIR"] = str(DATA_DIR)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["NEXSTUDIO_PARENTAL_DRYRUN"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nexstudio import app_api, parental, state, telegram  # noqa: E402
from nexstudio.i18n import clear_ui_cache, ui_tr  # noqa: E402


class MockTelegramState:
    def __init__(self):
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.valid_tokens = {"123456:VALID_BOT_TOKEN_abcdefghijk": "nex_test_bot"}
        self.calls = []  # list of dicts: {method, token, params, ts}
        self.updates = []  # list of update dicts
        self.next_update_id = 100
        self.next_msg_id = 1
        self.faults = {}  # method -> list of ("500",) | ("bad_json",) | ("ok_false", desc)
        self.max_offset_seen = 0
        self.get_updates_count = 0

    def push_update(self, payload):
        with self.cond:
            u = dict(payload)
            u.setdefault("update_id", self.next_update_id)
            self.next_update_id = max(self.next_update_id, u["update_id"]) + 1
            self.updates.append(u)
            self.cond.notify_all()
            return u["update_id"]

    def push_message(self, chat_id, text, update_id=None):
        p = {"message": {"message_id": self._alloc_msg_id(), "chat": {"id": chat_id}, "text": text}}
        if update_id is not None:
            p["update_id"] = update_id
        return self.push_update(p)

    def push_callback(self, chat_id, data, msg_id=1, msg_text="req", cq_id=None):
        cq_id = cq_id or f"cq_{time.time_ns()}"
        p = {
            "callback_query": {
                "id": cq_id,
                "data": data,
                "message": {"message_id": msg_id, "chat": {"id": chat_id}, "text": msg_text},
            }
        }
        return self.push_update(p)

    def _alloc_msg_id(self):
        mid = self.next_msg_id
        self.next_msg_id += 1
        return mid

    def inject_fault(self, method, fault):
        with self.cond:
            self.faults.setdefault(method, []).append(fault)
            self.cond.notify_all()

    def call_count(self, method=None):
        with self.lock:
            if method is None:
                return len(self.calls)
            return sum(1 for c in self.calls if c["method"] == method)

    def calls_for(self, method, since_index=0):
        with self.lock:
            return [c for c in self.calls[since_index:] if c["method"] == method]

    def wait_for_call(self, method, since_index=0, timeout=5.0, predicate=None):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                matches = [
                    c for c in self.calls[since_index:]
                    if c["method"] == method and (predicate is None or predicate(c))
                ]
                if matches:
                    return matches[-1]
                rem = deadline - time.monotonic()
                if rem <= 0:
                    return None
                self.cond.wait(rem)

    def wait_for_offset(self, target_offset, timeout=5.0):
        deadline = time.monotonic() + timeout
        with self.cond:
            while self.max_offset_seen < target_offset:
                rem = deadline - time.monotonic()
                if rem <= 0:
                    return False
                self.cond.wait(rem)
            return True


class ThreadingMockHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_handler(mock: MockTelegramState):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # silence stderr

        def _send_raw(self, status, body_bytes, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def _send_json(self, status, obj):
            self._send_raw(status, json.dumps(obj).encode("utf-8"))

        def do_POST(self):
            parsed = urlparse(self.path)
            parts = parsed.path.lstrip("/").split("/")
            if len(parts) < 2 or not parts[0].startswith("bot"):
                self._send_json(404, {"ok": False, "description": "Not Found"})
                return
            token = parts[0][3:]
            method = "/".join(parts[1:])

            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                params = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                params = {}

            with mock.cond:
                mock.calls.append({"method": method, "token": token, "params": params, "ts": time.monotonic()})
                fault_list = mock.faults.get(method)
                fault = fault_list.pop(0) if fault_list else None
                mock.cond.notify_all()

            if fault:
                kind = fault[0]
                if kind == "500":
                    self._send_raw(500, b"Internal Server Error", "text/plain")
                    return
                if kind == "bad_json":
                    self._send_raw(200, b"<<<not valid json>>>", "text/plain")
                    return
                if kind == "ok_false":
                    self._send_json(400, {"ok": False, "description": fault[1]})
                    return

            if token not in mock.valid_tokens:
                self._send_json(401, {"ok": False, "error_code": 401, "description": "Unauthorized"})
                return

            if method == "getMe":
                self._send_json(200, {
                    "ok": True,
                    "result": {"id": 999001, "is_bot": True, "username": mock.valid_tokens[token]},
                })
                return

            if method == "getUpdates":
                offset = int(params.get("offset") or 0)
                # Short long-poll capped at 0.35s for fast responsive tests
                poll_wait = min(float(params.get("timeout") or 0), 0.35)
                deadline = time.monotonic() + poll_wait
                with mock.cond:
                    mock.get_updates_count += 1
                    if offset > mock.max_offset_seen:
                        mock.max_offset_seen = offset
                    # Discard acknowledged updates (< offset) just like real Telegram
                    mock.updates = [u for u in mock.updates if u["update_id"] >= offset]
                    mock.cond.notify_all()
                    while not mock.updates:
                        rem = deadline - time.monotonic()
                        if rem <= 0:
                            break
                        mock.cond.wait(rem)
                        mock.updates = [u for u in mock.updates if u["update_id"] >= offset]
                    batch = list(mock.updates)
                self._send_json(200, {"ok": True, "result": batch})
                return

            if method == "sendMessage":
                with mock.cond:
                    mid = mock._alloc_msg_id()
                    mock.cond.notify_all()
                self._send_json(200, {
                    "ok": True,
                    "result": {
                        "message_id": mid,
                        "chat": {"id": params.get("chat_id")},
                        "text": params.get("text", ""),
                    },
                })
                return

            if method in ("answerCallbackQuery", "editMessageText"):
                self._send_json(200, {"ok": True, "result": True})
                return

            self._send_json(404, {"ok": False, "description": f"Unknown method: {method}"})

    return Handler


def run_suite():
    mock = MockTelegramState()
    server = ThreadingMockHTTPServer(("127.0.0.1", 0), make_handler(mock))
    port = server.server_address[1]
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    # Reset state like fresh config & point telegram.API to local mock
    state.APP_CONFIG = {}
    telegram.API = f"http://127.0.0.1:{port}/bot{{token}}/{{method}}"
    telegram._req.update(id="", state="", at=0.0, msg_id=0)
    parental.end_admin()

    results = []

    def check(name, fn):
        try:
            fn()
            print(f"PASS: {name}")
            results.append((name, True, ""))
        except Exception as e:
            print(f"FAIL: {name} -- {e}")
            traceback.print_exc()
            results.append((name, False, str(e)))

    try:
        # Prepare parental password for admin-gated tests
        parental.setup("ParentPass123!")
        parental.end_admin()

        # 1. set_token without admin session -> PermissionError
        def t_set_token_no_admin():
            try:
                telegram.set_token("123456:VALID_BOT_TOKEN_abcdefghijk")
                raise AssertionError("Expected PermissionError without admin session")
            except PermissionError:
                pass
            assert mock.call_count("getMe") == 0, "Should not call getMe without admin"

        check("set_token_requires_admin", t_set_token_no_admin)

        # 2. Invalid tokens rejected
        def t_invalid_tokens():
            parental.start_admin()
            bad_tokens = [
                "",
                None,
                "   ",
                "nocolonhere",
                "123456:has space",
                "123456:has\ttab",
                "123456:" + "a" * 100,  # > 100 chars
                "999999:UNKNOWN_TOKEN",  # rejected by mock getMe (401 ok:False)
            ]
            for tok in bad_tokens:
                try:
                    telegram.set_token(tok)
                    raise AssertionError(f"Expected ValueError for token={tok!r}")
                except ValueError:
                    pass
            assert not telegram.tg_cfg().get("token"), "Config token must remain empty after failed attempts"

        check("invalid_tokens_rejected", t_invalid_tokens)

        # 3. Valid token -> bot username from getMe + 6-digit pair_code
        pair_code_holder = {}

        def t_valid_token():
            res = telegram.set_token("123456:VALID_BOT_TOKEN_abcdefghijk")
            assert res["bot"] == "nex_test_bot", f"Unexpected bot: {res}"
            code = res["pair_code"]
            assert isinstance(code, str) and len(code) == 6 and code.isdigit(), f"Bad pair_code: {code!r}"
            pub = telegram.public()
            assert pub["bot"] == "nex_test_bot"
            assert pub["has_token"] is True
            assert pub["paired"] is False
            assert pub["pair_code"] == code
            assert "token" not in pub and "chat_id" not in pub
            pair_code_holder["code"] = code
            # Enable parental control so bridge loop stays active after pairing
            parental.save_settings({"enabled": True, "daily_min": 60, "start": "00:00", "end": "00:00"})
            # Ensure bridge loop thread is running
            telegram.start()
            assert telegram._thread is not None and telegram._thread.is_alive()

        check("valid_token_getMe_and_pair_code", t_valid_token)

        # 4. Pairing: "/start <wrong>" ignored, "/start <code>" pairs chat_id
        def t_pairing_wrong_ignored():
            wrong = "000000" if pair_code_holder["code"] != "000000" else "999999"
            before = mock.call_count()
            uid = mock.push_message(1001, f"/start {wrong}")
            assert mock.wait_for_offset(uid + 1, timeout=6.0), "Bridge loop did not poll wrong pairing update"
            time.sleep(0.15)
            assert telegram.paired() is False, "Wrong code must not pair"
            assert telegram.tg_cfg()["chat_id"] == 0
            assert len(mock.calls_for("sendMessage", before)) == 0, "Should not reply to wrong pair code"

        check("pairing_wrong_code_ignored", t_pairing_wrong_ignored)

        def t_pairing_valid_code():
            before = mock.call_count()
            uid = mock.push_message(1001, f"/start {pair_code_holder['code']}")
            sent = mock.wait_for_call("sendMessage", since_index=before, timeout=6.0)
            assert sent is not None, "Expected confirmation sendMessage after valid pairing"
            assert sent["params"]["chat_id"] == 1001
            assert "NexStudio" in sent["params"]["text"]
            assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert telegram.paired() is True
            assert telegram.tg_cfg()["chat_id"] == 1001
            assert telegram.tg_cfg()["pair_code"] == ""
            pub = telegram.public()
            assert pub["paired"] is True and pub["pair_code"] == ""

        check("pairing_valid_code_pairs_chat", t_pairing_valid_code)

        # 5. Messages from OTHER chats ignored (cannot grant time)
        def t_other_chat_messages_ignored():
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid1 = mock.push_message(2002, "/ekle 60")
            uid2 = mock.push_message(2002, "/durum")
            assert mock.wait_for_offset(uid2 + 1, timeout=6.0), "Bridge did not consume other-chat updates"
            time.sleep(0.15)
            assert parental.status()["extra_min"] == extra_before, "Other chat must not grant extra time"
            other_replies = [c for c in mock.calls_for("sendMessage", before) if c["params"].get("chat_id") == 2002]
            assert len(other_replies) == 0, f"Should not reply to other chat: {other_replies}"

        check("other_chat_messages_ignored", t_other_chat_messages_ignored)

        # 6. request_extra -> sendMessage with 4 buttons
        req_holder = {}

        def t_request_extra_4_buttons():
            # Ensure initial monotonic cooldown doesn't interfere even on freshly booted machine
            if time.monotonic() < telegram.REQUEST_COOLDOWN:
                telegram._req["at"] = -telegram.REQUEST_COOLDOWN
            before = mock.call_count()
            telegram.request_extra()
            sent = mock.wait_for_call("sendMessage", since_index=before, timeout=3.0)
            assert sent is not None, "Expected sendMessage from request_extra"
            assert sent["params"]["chat_id"] == 1001
            kb = sent["params"]["reply_markup"]["inline_keyboard"]
            buttons = [btn for row in kb for btn in row]
            assert len(buttons) == 4, f"Expected 4 inline buttons, got {len(buttons)}: {buttons}"
            st = telegram.request_state()
            rid = st["id"]
            assert st["state"] == "pending" and len(rid) == 8
            cb_datas = [b["callback_data"] for b in buttons]
            assert cb_datas == [f"x:{rid}:15", f"x:{rid}:30", f"x:{rid}:60", f"n:{rid}:0"], f"Unexpected callbacks: {cb_datas}"
            req_holder["rid"] = rid
            req_holder["msg_id"] = st["msg_id"]

        check("request_extra_sends_4_buttons", t_request_extra_4_buttons)

        # 7. Cooldown / pending prevents second request & callback from OTHER chat ignored
        def t_pending_prevents_second_and_other_chat_cb_ignored():
            try:
                telegram.request_extra()
                raise AssertionError("Expected ValueError while request is pending")
            except ValueError:
                pass
            # Callback from OTHER chat 2002 must be ignored
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid = mock.push_callback(2002, f"x:{req_holder['rid']}:30", msg_id=req_holder["msg_id"])
            assert mock.wait_for_offset(uid + 1, timeout=6.0)
            time.sleep(0.15)
            assert parental.status()["extra_min"] == extra_before, "Other chat callback must not grant time"
            assert telegram.request_state()["state"] == "pending"
            assert len(mock.calls_for("answerCallbackQuery", before)) == 0

        check("pending_blocks_second_and_other_chat_callback_ignored", t_pending_prevents_second_and_other_chat_cb_ignored)

        # 8. Callback "x:<id>:30" from parent chat -> grant_extra 30 & approved + cooldown still blocks second request
        def t_callback_approve_30():
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid = mock.push_callback(1001, f"x:{req_holder['rid']}:30", msg_id=req_holder["msg_id"], msg_text="⏰ Ek süre")
            edit = mock.wait_for_call("editMessageText", since_index=before, timeout=6.0)
            assert edit is not None, "Expected editMessageText after approval"
            ans = mock.wait_for_call("answerCallbackQuery", since_index=before, timeout=3.0)
            assert ans is not None and "+30" in ans["params"]["text"]
            assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert parental.status()["extra_min"] == extra_before + 30, f"Expected +30 extra_min, got {parental.status()['extra_min']}"
            assert telegram.request_state()["state"] == "approved"
            # Still within REQUEST_COOLDOWN -> second request must be rejected
            try:
                telegram.request_extra()
                raise AssertionError("Expected ValueError during cooldown after approval")
            except ValueError:
                pass

        check("callback_approve_grants_30_and_cooldown_blocks", t_callback_approve_30)

        # 9. Replayed / old callback id ignored
        def t_callback_replay_ignored():
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid = mock.push_callback(1001, f"x:{req_holder['rid']}:30", msg_id=req_holder["msg_id"])
            ans = mock.wait_for_call("answerCallbackQuery", since_index=before, timeout=6.0)
            assert ans is not None, "Expected answerCallbackQuery on replayed callback"
            assert "geçerli değil" in ans["params"]["text"]
            assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert parental.status()["extra_min"] == extra_before, "Replayed callback must NOT grant extra time"
            assert len(mock.calls_for("editMessageText", before)) == 0, "Replayed callback must not edit message"

        check("callback_replay_ignored", t_callback_replay_ignored)

        # 10. Callback "n:<id>:0" -> denied
        def t_callback_deny():
            # Expire cooldown so we can initiate a fresh request
            telegram._req["at"] = time.monotonic() - telegram.REQUEST_COOLDOWN - 5
            telegram.request_extra()
            st = telegram.request_state()
            rid2, mid2 = st["id"], st["msg_id"]
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid = mock.push_callback(1001, f"n:{rid2}:0", msg_id=mid2, msg_text="⏰ Ek süre")
            edit = mock.wait_for_call("editMessageText", since_index=before, timeout=6.0)
            assert edit is not None, "Expected editMessageText on denial"
            ans = mock.wait_for_call("answerCallbackQuery", since_index=before, timeout=3.0)
            assert ans is not None and "Reddedildi" in ans["params"]["text"]
            assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert telegram.request_state()["state"] == "denied"
            assert parental.status()["extra_min"] == extra_before, "Denied callback must not grant extra time"

        check("callback_deny_sets_denied", t_callback_deny)

        # 11. /ekle 45 grants 45 min
        def t_cmd_ekle_45():
            before = mock.call_count()
            extra_before = parental.status()["extra_min"]
            uid = mock.push_message(1001, "/ekle 45")
            sent = mock.wait_for_call("sendMessage", since_index=before, timeout=6.0)
            assert sent is not None, "Expected reply to /ekle 45"
            assert "+45" in sent["params"]["text"]
            assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert parental.status()["extra_min"] == extra_before + 45

        check("cmd_ekle_45_grants", t_cmd_ekle_45)

        # 12. /ekle abc and /ekle 999999 rejected with usage message
        def t_cmd_ekle_invalid():
            extra_before = parental.status()["extra_min"]
            for bad in ("/ekle abc", "/ekle 999999"):
                before = mock.call_count()
                uid = mock.push_message(1001, bad)
                sent = mock.wait_for_call("sendMessage", since_index=before, timeout=6.0)
                assert sent is not None, f"Expected usage reply for {bad}"
                assert "Kullanım: /ekle 30" in sent["params"]["text"], f"Unexpected reply for {bad}: {sent['params']['text']}"
                assert mock.wait_for_offset(uid + 1, timeout=5.0)
            assert parental.status()["extra_min"] == extra_before

        check("cmd_ekle_invalid_rejected", t_cmd_ekle_invalid)

        # 13. /durum replies with status
        def t_cmd_durum():
            before = mock.call_count()
            uid = mock.push_message(1001, "/durum")
            sent = mock.wait_for_call("sendMessage", since_index=before, timeout=6.0)
            assert sent is not None, "Expected reply to /durum"
            txt = sent["params"]["text"]
            assert "Bugün:" in txt and "Durum:" in txt, f"Unexpected status text: {txt}"
            assert mock.wait_for_offset(uid + 1, timeout=5.0)

        check("cmd_durum_replies_status", t_cmd_durum)

        # 14. set_report_time validation
        def t_set_report_time_validation():
            parental.end_admin()
            try:
                telegram.set_report_time("20:00")
                raise AssertionError("Expected PermissionError without admin")
            except PermissionError:
                pass
            parental.start_admin()
            for bad in ("25:00", "24:00", "12:60", "9:00", "12:5", "ab:cd", "", None, "12:00:00"):
                try:
                    telegram.set_report_time(bad)
                    raise AssertionError(f"Expected ValueError for report_time={bad!r}")
                except ValueError:
                    pass
            telegram.set_report_time("23:59")
            assert telegram.tg_cfg()["report_time"] == "23:59"
            telegram.set_report_time("00:00")
            assert telegram.tg_cfg()["report_time"] == "00:00"

        check("set_report_time_validation", t_set_report_time_validation)

        # 15. Daily report sent once per day after report_time
        def t_daily_report_once():
            today = datetime.now().strftime("%Y-%m-%d")
            now_hm = datetime.now().strftime("%H:%M")
            # Clear last_report and set future report_time if possible
            telegram.tg_cfg()["last_report"] = ""
            if now_hm < "23:59":
                telegram.set_report_time("23:59")
                before = mock.call_count()
                telegram._maybe_report()
                reports = [c for c in mock.calls_for("sendMessage", before) if "Günlük rapor" in c["params"].get("text", "")]
                assert len(reports) == 0, "Should not send daily report before report_time"

            # Set report_time <= now ("00:00") and wait for bridge loop to send it once
            before = mock.call_count()
            telegram.set_report_time("00:00")
            rep = mock.wait_for_call(
                "sendMessage",
                since_index=before,
                timeout=6.0,
                predicate=lambda c: "Günlük rapor" in c["params"].get("text", ""),
            )
            assert rep is not None, "Expected daily report after report_time"
            for _ in range(20):   # rapor gönderildikten hemen sonra yazılır
                if telegram.tg_cfg()["last_report"] == today:
                    break
                time.sleep(0.1)
            assert telegram.tg_cfg()["last_report"] == today, "last_report not saved"

            # Ensure not sent a second time today
            before2 = mock.call_count()
            telegram._maybe_report()
            time.sleep(0.5)
            rep2 = [c for c in mock.calls_for("sendMessage", before2) if "Günlük rapor" in c["params"].get("text", "")]
            assert len(rep2) == 0, f"Daily report sent more than once today: {rep2}"

        check("daily_report_sent_once_per_day", t_daily_report_once)

        # 16. AppApi wiring (tg_test, tg_report_time, get_parental, remote blocked)
        def t_app_api_wiring():
            # Remote blocked with 403
            code, res = app_api.AppApi.dispatch("GET", "parental", {}, remote=True)
            assert code == 403 and res["ok"] is False
            code, res = app_api.AppApi.dispatch("POST", "parental", {"op": "tg_test"}, remote=True)
            assert code == 403 and res["ok"] is False

            # Local without admin: get_parental hides telegram, tg_test fails with 400
            parental.end_admin()
            code, res = app_api.AppApi.dispatch("GET", "parental", {}, remote=False)
            assert code == 200 and res["telegram"] is None
            code, res = app_api.AppApi.dispatch("POST", "parental", {"op": "tg_test"}, remote=False)
            assert code == 400 and res["ok"] is False

            # Local with admin: get_parental shows public telegram, tg_test sends message
            parental.start_admin()
            code, res = app_api.AppApi.dispatch("GET", "parental", {}, remote=False)
            assert code == 200 and res["telegram"]["paired"] is True and "token" not in res["telegram"]
            before = mock.call_count()
            code, res = app_api.AppApi.dispatch("POST", "parental", {"op": "tg_test"}, remote=False)
            assert code == 200 and res["ok"] is True
            sent = mock.wait_for_call("sendMessage", since_index=before, timeout=3.0)
            assert sent is not None and "deneme mesajı" in sent["params"]["text"]
            code, res = app_api.AppApi.dispatch("POST", "parental", {"op": "tg_report_time", "value": "20:30"}, remote=False)
            assert code == 200 and telegram.tg_cfg()["report_time"] == "20:30"

        check("app_api_parental_telegram_wiring", t_app_api_wiring)

        # 17. Bridge loop survives mock server errors (HTTP 500 & invalid JSON) without crashing
        def t_loop_survives_errors():
            # Verify _call raises on 500 and invalid JSON directly first
            mock.inject_fault("getMe", ("500",))
            try:
                telegram._call("getMe")
                raise AssertionError("Expected error on HTTP 500")
            except Exception:
                pass
            mock.inject_fault("getMe", ("bad_json",))
            try:
                telegram._call("getMe")
                raise AssertionError("Expected error on invalid JSON")
            except Exception:
                pass

            # Now test the REAL running _loop() thread surviving HTTP 500 and invalid JSON!
            # Wait for 500 fault to be hit by getUpdates
            before = mock.call_count()
            mock.inject_fault("getUpdates", ("500",))
            hit500 = mock.wait_for_call("getUpdates", since_index=before, timeout=5.0)
            assert hit500 is not None, "Loop did not call getUpdates for 500 test"
            time.sleep(0.3)
            assert telegram._thread.is_alive(), "Bridge loop crashed on HTTP 500!"

            # Wait for 15s error backoff to elapse and hit invalid JSON fault next
            before2 = mock.call_count()
            mock.inject_fault("getUpdates", ("bad_json",))
            hit_bad = mock.wait_for_call("getUpdates", since_index=before2, timeout=18.0)
            assert hit_bad is not None, "Loop did not recover after 500 backoff"
            time.sleep(0.3)
            assert telegram._thread.is_alive(), "Bridge loop crashed on invalid JSON!"

            # Wait for recovery after invalid JSON backoff and prove loop still handles messages!
            before3 = mock.call_count()
            uid = mock.push_message(1001, "/durum")
            sent = mock.wait_for_call("sendMessage", since_index=before3, timeout=18.0)
            assert sent is not None and "Bugün:" in sent["params"]["text"], "Loop did not recover after invalid JSON"
            assert mock.wait_for_offset(uid + 1, timeout=5.0)

        check("loop_survives_500_and_invalid_json", t_loop_survives_errors)

        # 18. LockWindow btn_request visibility/enabled state (offscreen Qt)
        def t_lock_window_btn_request():
            from PyQt5.QtWidgets import QApplication
            from nexstudio.parental_ui import LockWindow

            app = QApplication.instance() or QApplication([])
            screens = app.screens()
            if not screens:
                return
            dummy_guard = type("G", (), {"locked": False, "tick": lambda self: None, "hide_lock": lambda self: None})()
            win = LockWindow(dummy_guard, screens[0])
            try:
                telegram._req["state"] = ""
                st_limit = {
                    "reason": "limit", "used_min": 60, "start": "07:00", "end": "22:00", "dry_run": True
                }
                win.update_texts(st_limit)
                assert not win.btn_request.isHidden(), "btn_request should be visible when reason=limit and paired"
                assert win.btn_request.isEnabled(), "btn_request should be enabled when not pending"

                telegram._req["state"] = "pending"; telegram._req["at"] = time.monotonic()
                win.update_texts(st_limit)
                assert not win.btn_request.isEnabled(), "btn_request should be disabled when pending"
                assert "bekleniyor" in win.req_info.text()

                st_hours = {
                    "reason": "hours", "used_min": 10, "start": "07:00", "end": "22:00", "dry_run": True
                }
                win.update_texts(st_hours)
                assert win.btn_request.isHidden(), "btn_request should be hidden when reason=hours"
            finally:
                win.close()
                win.deleteLater()

        check("lock_window_btn_request_state", t_lock_window_btn_request)

        # 19. disconnect clears token and chat (and requires admin)
        def t_disconnect():
            parental.end_admin()
            try:
                telegram.disconnect()
                raise AssertionError("Expected PermissionError for disconnect without admin")
            except PermissionError:
                pass
            parental.start_admin()
            telegram.disconnect()
            t = telegram.tg_cfg()
            assert t["token"] == "" and t["chat_id"] == 0 and t["pair_code"] == "" and t["bot"] == ""
            assert telegram.paired() is False
            pub = telegram.public()
            assert pub["has_token"] is False and pub["paired"] is False

        check("disconnect_clears_token_and_chat", t_disconnect)

        # ----- Diagnostic probes for security/bug report (informational only) -----
        print("\n--- Diagnostic Bug/Security Probes (for REPORT.md) ---")

        # Probe 1: Token leakage in requests.ConnectionError string
        try:
            orig_api = telegram.API
            telegram.API = "http://127.0.0.1:1/bot{token}/{method}"
            try:
                telegram._call("sendMessage", token="123456:SECRET_LEAK_TOKEN_abcdefghij", http_timeout=1, chat_id=1, text="hi")
            except Exception as e:
                leaked = "123456:SECRET_LEAK_TOKEN_abcdefghij" in str(e)
                print(f"PROBE [token_in_connection_error]: leaked={leaked} err={str(e)[:140]}")
        finally:
            telegram.API = orig_api

        # Probe 2: English translation bug: ui_tr("Açık") -> "Light" & hardcoded "dk"
        state.APP_CONFIG["language"] = "en"
        clear_ui_cache()
        status_en = telegram._status_text()
        print(f"PROBE [en_status_text]: {status_en!r}")
        state.APP_CONFIG["language"] = "tr"
        clear_ui_cache()

        # Probe 3: Token validation accepts URL path/query characters
        mock.valid_tokens["123:abc"] = "weird_bot"
        try:
            r_inj = telegram.set_token("123:abc/sendMessage?chat_id=1#")
            print(f"PROBE [token_path_injection]: accepted_and_saved=True result={r_inj!r}")
        except ValueError as e:
            print(f"PROBE [token_path_injection]: accepted_and_saved=False passed_validation={str(e) != 'Bot anahtarı geçersiz'} err={e!r}")

        # Probe 4: _maybe_report marks last_report BEFORE send() succeeds
        telegram.tg_cfg().update(token="123456:VALID_BOT_TOKEN_abcdefghijk", chat_id=1001, report_time="00:00", last_report="")
        mock.inject_fault("sendMessage", ("500",))
        try:
            telegram._maybe_report()
        except Exception:
            pass
        print(f"PROBE [report_marked_on_send_failure]: last_report={telegram.tg_cfg()['last_report']!r}")

        # Probe 5: Malformed callback minutes mutates _req['state'] to 'approved' before ValueError
        telegram._req.update(id="deadbeef", state="pending", at=time.monotonic(), msg_id=9)
        try:
            telegram._handle({"callback_query": {"id": "cq_bad", "data": "x:deadbeef:notanint",
                                                 "message": {"message_id": 9, "chat": {"id": 1001}, "text": "t"}}})
        except ValueError:
            pass
        print(f"PROBE [bad_callback_mutates_state]: state={telegram._req['state']!r}")

        # Probe 6: Pending request stays blocked even after REQUEST_COOLDOWN elapsed
        telegram._req.update(id="deadbeef", state="pending", at=time.monotonic() - 9999, msg_id=9)
        try:
            telegram.request_extra()
            stuck = False
        except ValueError:
            stuck = True
        print(f"PROBE [pending_never_expires]: blocked_after_9999s={stuck}")

        # Probe 7: stop() followed immediately by start() while thread still alive leaves _stop set
        # (Stop cleanly at the end of all tests)
    finally:
        telegram.stop()
        if telegram._thread and telegram._thread.is_alive():
            telegram._thread.join(timeout=3.0)
        server.shutdown()
        server.server_close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} geçti")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_suite())
