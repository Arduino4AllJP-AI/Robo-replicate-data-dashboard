from flask import Flask, render_template_string, request, redirect, jsonify
import os
import webbrowser
import threading
import pyodbc
import json
import subprocess
import psutil

app = Flask(__name__)
CONFIG_FILE = "config.txt"
BRIDGE_SCRIPT = "mqtt_bridge_sql_influx.py"

# === Check if Bridge is Running ===
def is_bridge_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and BRIDGE_SCRIPT in ' '.join(proc.info['cmdline']):
                return True
        except Exception:
            pass
    return False

# === Load Config from TEXT file ===
def load_config():
    config = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    except:
        pass
    return config

# === Save Config to TEXT file ===
def save_config(new_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for k, v in new_data.items():
                f.write(f"{k}={v}\n")
    except:
        pass

# === Get SQL Device Info (last-seen per DEV_EUI) ===
def get_devices_with_timestamp():
    cfg = load_config()
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={cfg.get('SQL_SERVER','')};"
            f"DATABASE={cfg.get('SQL_DATABASE','')};Trusted_Connection=yes;"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                js.device,
                MAX(h.timestamp) AS last_seen
            FROM [Field_devices_data].[dbo].[historical_data] h
            CROSS APPLY (
                SELECT JSON_VALUE(h.json_data, '$.DEV_EUI') AS device
            ) AS js
            WHERE js.device IS NOT NULL
            GROUP BY js.device
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # return mapping of device → ISO timestamp string
        return { r.device: r.last_seen.isoformat(sep=' ') for r in rows }
    except:
        return {}

@app.route("/status")
def bridge_status_check():
    return jsonify({"running": is_bridge_running()})

@app.route("/devices")
def live_device_data():
    return jsonify(get_devices_with_timestamp())

@app.route("/", methods=["GET", "POST"])
def index():
    dark = request.args.get("dark") == "on"
    page = request.args.get("page", "dashboard")
    config = load_config()

    # handle saving credentials
    if request.method == "POST" and page == "edit":
        save_config(request.form)
        return redirect(f"/?page=credentials&dark={'on' if dark else 'off'}")

    # load device data only on dashboard
    device_data = get_devices_with_timestamp() if page == "dashboard" else {}
    msg = ""

    # run bridge script on demand
    if request.args.get("run") == "1":
        try:
            subprocess.Popen(["python", BRIDGE_SCRIPT])
            msg = "✅ Bridge script launched."
        except Exception as e:
            msg = f"❌ Error launching bridge script: {e}"

    # render inline template
    return render_template_string("""<!DOCTYPE html>
<html>
<head>
    <title>🤖Tele_ROBO_Bridge</title>
    <style>
        body { background-color: {{ '#1e1e1e' if dark else '#ffffff' }}; color: {{ '#ffffff' if dark else '#000000' }}; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
        .sidebar { width: 180px; background-color: {{ '#222' if dark else '#e6e6e6' }}; padding: 10px; float: left; height: 100vh; text-align: center; }
        .sidebar img { width: 90px; margin-bottom: 15px; }
        .sidebar a { display: block; background-color: {{ '#444' if dark else '#ccc' }}; color: {{ '#fff' if dark else '#000' }}; text-decoration: none; padding: 10px; margin-bottom: 8px; border-radius: 4px; }
        .sidebar a:hover { background-color: #00ffaa; color: black; }
        .main { margin-left: 200px; padding: 20px; }
        h1 { font-size: 20px; color: #00ffaa; }
        input[type=text] { padding: 6px; width: 300px; margin-bottom: 10px; background: {{ '#2e2e2e' if dark else '#fff' }}; color: {{ '#fff' if dark else '#000' }}; border: 1px solid #888; border-radius: 4px; }
        pre { background: #fff; padding: 10px; border-radius: 5px; color: #000; max-width: 600px; }
        .notice { background: #ffdddd; color: red; border: 1px solid red; padding: 8px; margin-top: 10px; border-radius: 5px; font-weight: bold; }
        button { padding: 10px 15px; background-color: #00ffaa; border: none; color: black; font-weight: bold; cursor: pointer; margin-top: 10px; }
    </style>
    <script>
        function checkBridgeStatus() {
            fetch("/status").then(r => r.json()).then(d => {
                const el = document.getElementById("bridge_status");
                el.innerText = d.running ? '🟢 Running' : '🔴 Not Running';
                el.style.color = d.running ? 'lightgreen' : 'red';
            });
        }
        function updateDevices() {
            fetch("/devices").then(r => r.json()).then(d => {
                let out = '';
                for (const [dev, ts] of Object.entries(d)) {
                    out += `${dev}   →   Last seen: ${ts}\n`;
                }
                document.getElementById("device_output").textContent = out || 'No devices found.';
            });
        }
        setInterval(() => { checkBridgeStatus(); updateDevices(); }, 3000);
        window.onload = () => { checkBridgeStatus(); updateDevices(); };
    </script>
</head>
<body>
<div class="sidebar">
    <img src="/static/logo.png" alt="Logo">
    <a href="/?page=dashboard&dark={{ 'on' if dark else 'off' }}">Dashboard</a>
    <a href="/?page=credentials&dark={{ 'on' if dark else 'off' }}">Credentials</a>
    <a href="/?page=edit&dark={{ 'on' if dark else 'off' }}">Edit Credentials</a>
    <form method="get" style="margin-top:20px;"><input type="hidden" name="page" value="{{ page }}">
        <label><input type="checkbox" name="dark" value="on" onchange="this.form.submit();" {% if dark %}checked{% endif %}> Dark Mode</label>
    </form>
</div>
<div class="main">
    <h1>🤖Tele_ROBO_Bridge</h1>
    {% if msg %}<div class="notice">{{ msg }}</div>{% endif %}
    {% if page == 'credentials' %}
        <h2>Config File</h2><pre>{{ open(CONFIG_FILE).read() if os.path.exists(CONFIG_FILE) else '' }}</pre>
    {% elif page == 'edit' %}
        <h2>Edit Credentials</h2>
        <form method="post">
            {% for k, v in config.items() %}
                <label>{{ k }}</label><br><input type="text" name="{{ k }}" value="{{ v }}"><br>
            {% endfor %}
            <button type="submit">💾 Save</button>
        </form>
    {% elif page == 'dashboard' %}
        <p><strong>Bridge Status:</strong> <span id="bridge_status">🔄 Checking.</span></p>
        <h2>Found Devices:</h2>
        <pre id="device_output">🔄 Loading.</pre>
        <form method="get"><input type="hidden" name="run" value="1"><input type="hidden" name="page" value="dashboard"><input type="hidden" name="dark" value="{{ 'on' if dark else 'off' }}"><button type="submit">▶️ Run MQTT Bridge</button></form>
    {% endif %}
</div>
</body>
</html>""",
        config=config,
        dark=dark,
        page=page,
    )

def open_browser():
    webbrowser.open("http://127.0.0.1:5050")

if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    app.run(debug=False, port=5050)
