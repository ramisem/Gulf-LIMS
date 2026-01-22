import pythoncom
import win32com.client
import io
from flask import Flask, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import time
from websocket import create_connection
import json
import threading

app = Flask(__name__)
CORS(app)

# -------- LOCAL TESTING ENDPOINTS --------
WS_URL = "ws://ec2-3-85-112-56.compute-1.amazonaws.com:8001/ws/agent/agent1/"
# WS_URL = "ws://127.0.0.1:8001/ws/agent/agent1/"
# UPLOAD_URL = "http://127.0.0.1:8000/api/scan-upload"
UPLOAD_URL = "http://ec2-3-85-112-56.compute-1.amazonaws.com/api/scan-upload"

scan_lock = threading.Lock()

# -------- REAL SCANNER (WIA) --------
def perform_scan():
    pythoncom.CoInitialize()
    wia = win32com.client.Dispatch("WIA.CommonDialog")
    image = wia.ShowAcquireImage(1, 0)

    if image is None:
        raise Exception("No image acquired")

    img_bytes = io.BytesIO(image.FileData.BinaryData)
    img = Image.open(img_bytes)

    out_bytes = io.BytesIO()
    img.save(out_bytes, format="PNG")
    out_bytes.seek(0)

    return out_bytes.getvalue()


# -------- FAKE SCAN (SIMULATED SCANNER) --------
def generate_fake_scan():
    img = Image.new("RGB", (850, 1100), "white")
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((50, 40), "Gulf Coast Pathologists", fill="black")
    draw.text((50, 100), "Simulated Scanner Output", fill="black")

    # Fake text lines
    for i in range(10):
        draw.text((50, 180 + i * 40), f"Line {i+1}: Sample text scanned...", fill="black")

    # Fake stamp
    draw.ellipse((600, 900, 830, 1030), outline="red", width=5)
    draw.text((620, 925), "SIMULATED", fill="red")

    # Blur to mimic real scan
    img = img.filter(ImageFilter.GaussianBlur(1.5))

    out_bytes = io.BytesIO()
    img.save(out_bytes, format="PNG")
    out_bytes.seek(0)

    return out_bytes.getvalue()   # ✔ FIXED: RETURN BYTES


# -------- FLASK ENDPOINTS --------
@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


@app.route("/scan")
def scan_preview():
    """
    IMPORTANT:
    Do NOT call the real scanner here.
    This endpoint should NOT open scanner popup.
    """
    img_bytes = generate_fake_scan()
    return send_file(io.BytesIO(img_bytes), mimetype="image/png")


# -------- UPLOAD SCAN TO DJANGO --------
def upload_scan(request_id, data):
    files = {"file": ("scan.png", data, "image/png")}
    r = requests.post(UPLOAD_URL, files=files, data={"request_id": request_id})
    return r.json()


# -------- WEBSOCKET LISTENER --------
def ws_listener():
    while True:
        try:
            print("Connecting to WebSocket:", WS_URL)
            ws = create_connection(WS_URL)

            # Send unique session handshake to avoid old messages
            ws.send(json.dumps({
                "type": "hello",
                "agent": "agent1",
                "session": str(time.time())
            }))

            while True:
                msg = ws.recv()
                if not msg:
                    break

                data = json.loads(msg)

                # ----- START SCAN ACTION -----
                if data.get("action") == "start_scan":
                    request_id = data["request_id"]
                    print("Scan request received:", request_id)

                    # Prevent duplicate popup
                    if scan_lock.locked():
                        print("Scanner already in use. Ignoring duplicate request.")
                        continue

                    with scan_lock:
                        try:
                            scan_bytes = perform_scan()

                            upload_res = upload_scan(request_id, scan_bytes)

                            ws.send(json.dumps({
                                "type": "scan_complete",
                                "request_id": request_id,
                                "file_url": upload_res.get("file_url")
                            }))

                            print("Scan uploaded:", upload_res.get("file_url"))

                        except Exception as e:
                            ws.send(json.dumps({
                                "type": "scan_error",
                                "request_id": request_id,
                                "error": str(e)
                            }))

        except Exception as e:
            print("WebSocket Error:", e)
            time.sleep(5)


# -------- MAIN --------
if __name__ == "__main__":
    import os, sys

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, "config.json")

    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        host = config.get("HOST", "0.0.0.0")
        port = config.get("PORT", 5000)
    else:
        host = "0.0.0.0"
        port = 5000

    threading.Thread(target=ws_listener, daemon=True).start()

    app.run(host=host, port=port)
