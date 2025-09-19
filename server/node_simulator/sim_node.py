#!/usr/bin/env python3
"""Energy Node Simulator
- Simulates voltage & current sampling, computes RMS & power values.
- Exposes a Modbus/TCP server (port 5020) with telemetry in holding registers.
- Provides a Flask web dashboard (port 5000) + OTA upload endpoints.
- Uses AES-256-CBC for encrypting the OTA firmware file.
"""

import threading, time, math, os
from http import HTTPStatus
from flask import Flask, jsonify, send_file, request, render_template
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import numpy as np

# -------------------------------------------------------
# Config
MODBUS_PORT = 5020        # Use non-privileged port if necessary (502 requires root/admin)
MODBUS_ADDR = ("0.0.0.0", MODBUS_PORT)
FLASK_PORT = 5000
OTA_DIR = "ota_files"
AES_KEY = b"This_is_a_32_byte_key_for_AES_256!!"[:32]  # Example key (change in production)

# Holding register map (simple scaled integers)
# 40001 : voltage (V * 100) -> int
# 40002 : current (A * 1000)
# 40003 : active power (W * 10)
# 40004 : reactive power (VAR * 10)
# 40005 : power factor (PF * 1000)
# 40006 : frequency (Hz * 100)
# 40010-40011 : 32-bit timestamp (seconds since epoch, split into two 16-bit registers)
# ... extend as needed

app = Flask(__name__)
app.secret_key = "dev-secret-key"

os.makedirs(OTA_DIR, exist_ok=True)

# Shared telemetry state
telemetry = {
    "voltage": 230.0,
    "current": 1.23,
    "active_power": 283.0,
    "reactive_power": 20.0,
    "pf": 0.95,
    "frequency": 50.0,
    "timestamp": int(time.time())
}

# -------------------- Modbus setup --------------------
store = ModbusSlaveContext(hr={})
context = ModbusServerContext(slaves=store, single=True)

def telemetry_to_registers(t):
    """Convert telemetry floats to scaled 16-bit registers (unsigned)."""
    regs = {}
    regs[0] = int(round(t["voltage"] * 100)) & 0xFFFF
    regs[1] = int(round(t["current"] * 1000)) & 0xFFFF
    regs[2] = int(round(t["active_power"] * 10)) & 0xFFFF
    regs[3] = int(round(t["reactive_power"] * 10)) & 0xFFFF
    regs[4] = int(round(t["pf"] * 1000)) & 0xFFFF
    regs[5] = int(round(t["frequency"] * 100)) & 0xFFFF
    ts = int(t.get("timestamp", time.time()))
    low = ts & 0xFFFF
    high = (ts >> 16) & 0xFFFF
    regs[9] = high
    regs[10] = low
    return regs

def modbus_updater_thread():
    while True:
        regs = telemetry_to_registers(telemetry)
        hr = [0]*125  # default size
        # fill hr with values at offsets (40001 -> index 0)
        for i,v in regs.items():
            if i < len(hr):
                hr[i] = v
        store.setValues(3, 0, hr)  # 3 = holding registers
        time.sleep(1.0)

# -------------------- Telemetry generation --------------------
class SignalSimulator(threading.Thread):
    def __init__(self, sample_rate=2000, window_seconds=1.0):
        super().__init__(daemon=True)
        self.sample_rate = sample_rate
        self.window_seconds = window_seconds
        self.samples = int(sample_rate * window_seconds)
        self.t = 0.0
        self.running = True

    def run(self):
        while self.running:
            # generate a short window of samples
            ts = np.linspace(0, self.window_seconds, self.samples, endpoint=False)
            # fundamental frequency (50Hz)
            f = telemetry["frequency"]
            v = 230.0 * np.sin(2*np.pi*f*ts + (time.time() % (2*np.pi)))
            # small noise + harmonic example
            v += 1.0 * np.sin(2*np.pi*3*f*ts) * 0.01
            i = 1.23 * np.sin(2*np.pi*f*ts - 0.1)  # phase shift for PF
            # calculate RMS and instantaneous power
            vrms = np.sqrt(np.mean(v*v))
            irms = np.sqrt(np.mean(i*i))
            inst_power = v * i
            p_active = np.mean(inst_power)
            # update global telemetry (thread-safe enough for demo)
            telemetry["voltage"] = float(np.round(vrms, 3))
            telemetry["current"] = float(np.round(irms, 4))
            telemetry["active_power"] = float(np.round(p_active, 3))
            # reactive power approximated (q = sqrt(s^2 - p^2))
            s = vrms * irms
            q = max(0.0, np.sqrt(max(0.0, s*s - p_active*p_active)))
            telemetry["reactive_power"] = float(np.round(q, 3))
            telemetry["pf"] = float(np.round(p_active / s if s>0 else 0.0, 3))
            telemetry["timestamp"] = int(time.time())
            time.sleep(self.window_seconds * 0.9)

# -------------------- OTA helpers --------------------
def aes_encrypt_bytes(plain_bytes, key):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # PKCS7 padding
    pad_len = 16 - (len(plain_bytes) % 16)
    padded = plain_bytes + bytes([pad_len])*pad_len
    ct = cipher.encrypt(padded)
    return iv + ct

def aes_decrypt_bytes(enc_bytes, key):
    iv = enc_bytes[:16]
    ct = enc_bytes[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = cipher.decrypt(ct)
    pad_len = padded[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid padding")
    return padded[:-pad_len]

# -------------------- Flask app (dashboard + OTA) --------------------
@app.route("/api/telemetry")
def api_telemetry():
    return jsonify(telemetry)

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/ota/upload", methods=["POST"])
def ota_upload():
    # Accepts multipart form file 'firmware' or raw body for simpler clients
    file = None
    if "firmware" in request.files:
        file = request.files["firmware"].read()
    else:
        file = request.data or None
    if not file:
        return ("No file provided", HTTPStatus.BAD_REQUEST)
    # Encrypt with AES and store
    enc = aes_encrypt_bytes(file, AES_KEY)
    fname = os.path.join(OTA_DIR, "firmware.enc")
    with open(fname, "wb") as f:
        f.write(enc)
    return ("Firmware uploaded and encrypted", HTTPStatus.OK)

@app.route("/ota/apply", methods=["POST"])
def ota_apply():
    fname = os.path.join(OTA_DIR, "firmware.enc")
    if not os.path.exists(fname):
        return ("No encrypted firmware present", HTTPStatus.BAD_REQUEST)
    with open(fname, "rb") as f:
        enc = f.read()
    try:
        dec = aes_decrypt_bytes(enc, AES_KEY)
    except Exception as e:
        return (f"Decrypt failed: {e}", HTTPStatus.INTERNAL_SERVER_ERROR)
    applied_path = os.path.join(OTA_DIR, "firmware_applied.bin")
    with open(applied_path, "wb") as f:
        f.write(dec)
    return ("Firmware decrypted and applied (simulated)", HTTPStatus.OK)

@app.route("/ota/download-encrypted")
def ota_download_enc():
    fname = os.path.join(OTA_DIR, "firmware.enc")
    if not os.path.exists(fname):
        return ("No encrypted firmware present", HTTPStatus.NOT_FOUND)
    return send_file(fname, as_attachment=True, download_name="firmware.enc")


def run_modbus():
    # start modbus updater thread and run server
    t = threading.Thread(target=modbus_updater_thread, daemon=True)
    t.start()
    # Start synchronous Modbus TCP server (blocking call)
    print("Starting Modbus/TCP server on port", MODBUS_PORT)
    StartTcpServer(context, address=MODBUS_ADDR)

if __name__ == '__main__':
    # start telemetry generator
    s = SignalSimulator()
    s.start()
    # start modbus server in a thread to allow flask to run
    mthread = threading.Thread(target=run_modbus, daemon=True)
    mthread.start()
    # start flask app
    print("Starting Flask dashboard on port", FLASK_PORT)
    app.run(host='0.0.0.0', port=FLASK_PORT)
