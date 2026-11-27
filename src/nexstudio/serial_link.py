# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Arduino ile seri haberleşme (SerialThread)."""
from . import state
from .core import (  # noqa: F401
    QThread,
    pyqtSignal,
    serial,
    threading,
    time,
    write_error_log,
)

# =========================================================
# 6. SERİ PORT HABERLEŞMESİ (ARDUINO)
# =========================================================
class SerialThread(QThread):
    """
    Arduino ile seri haberleşme.
    2.0: kendi satır tamponu (yarım satır gelmez), kopma algılama, thread-güvenli yazma,
    port kapatma işlemini okuma thread'inin kendisi yapar (yarış durumu yok).
    """
    data_received = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    connected = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.serial_conn = None
        self.is_running = True
        self._stop_requested = False
        self._write_lock = threading.Lock()
        self.last_rx = time.monotonic()

    def run(self):
        buf = b""
        try:
            self.serial_conn = serial.Serial(self.port, 9600, timeout=0.05, write_timeout=1)
            try:
                self.serial_conn.dtr = True  # Pro Micro (32U4) USB-CDC, DTR olmadan veri göndermeyebilir.
            except Exception:
                pass
            self.last_rx = time.monotonic()
            self.connected.emit(self.port)
            self.send_data("HELLO\n")  # 2.0 firmware kimlik bilgisi döner; eski firmware yok sayar.
            while not self._stop_requested:
                chunk = self.serial_conn.read(self.serial_conn.in_waiting or 1)
                if not chunk:
                    continue
                self.last_rx = time.monotonic()
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("utf-8", errors="ignore").strip()
                    if text:
                        self.data_received.emit(text)
                if len(buf) > 1024:
                    buf = b""
        except Exception as e:
            if not self._stop_requested:
                self.connection_error.emit(str(e))
        finally:
            self.is_running = False
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception:
                pass

    def send_data(self, data_str):
        conn = self.serial_conn
        if not conn or not conn.is_open:
            return False
        with self._write_lock:
            try:
                conn.write(data_str.encode("iso-8859-9", errors="replace"))
                return True
            except Exception as e:
                write_error_log(f"Seri yazma hatası ({self.port}): {e}")
                return False

    def stop(self):
        self._stop_requested = True
