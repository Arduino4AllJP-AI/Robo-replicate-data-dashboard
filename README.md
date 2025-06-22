# Robo Replicate Data Dashboard

**A real-time data bridge & dashboard for MQTT → InfluxDB + SQL Server**

This project consists of two Python components:

1. **`mqtt_bridge_sql_influx.py`**

   * Subscribes to a specified MQTT topic.
   * Parses incoming JSON payloads.
   * Writes data points to InfluxDB (if configured).
   * Logs or circularly stores the latest 100 records in a SQL Server table.
   * Exports the latest 100 records to `historical_data.csv`.

2. **`Tele_Robo_Bridge.py`**

   * A Flask-based dashboard and control panel.
   * Shows current bridge status (running/not running).
   * Displays a live list of devices and their last-seen timestamps from SQL Server.
   * Allows on-demand launch of the MQTT bridge script.
   * Provides a dark/light theme toggle.

---

## 🚀 Key Features

* **MQTT Integration**: Reliable subscription with retry logic.
* **Dual Storage**: Pushes telemetry to InfluxDB and a SQL Server table.
* **Circular Buffer**: Keeps only the latest 100 rows in SQL to prevent unbounded growth.
* **CSV Export**: Automatic snapshot of recent data in `historical_data.csv`.
* **Web Dashboard**: Simple Flask UI to monitor bridge status and device activity.
* **Configurable**: All connection parameters in a single `config.txt` file.

---

## 📋 Prerequisites

* **Windows 10/11** (or any OS with Windows-style batch support)
* **Python 3.8+**
* **MQTT broker** (hostname, port, credentials)
* **InfluxDB** (URL, token, org, bucket)
* **SQL Server** (ODBC driver 17)
* **Git** (to clone/update the repo)

---

## 🔧 Installation & Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Arduino4AllJP-AI/Robo-replicate-data-dashboard.git
   cd Robo-replicate-data-dashboard
   ```

2. **Edit `config.txt`** with your connection details:

   ```text
   # MQTT settings
   MQTT_BROKER=broker.example.com
   MQTT_PORT=8883
   MQTT_TOPIC=your/topic/#
   MQTT_USERNAME=optional_user
   MQTT_PASSWORD=optional_pass

   # InfluxDB settings
   INFLUX_URL=http://localhost:8086
   INFLUX_TOKEN=your_token_here
   INFLUX_ORG=your_org
   INFLUX_BUCKET=your_bucket

   # SQL Server settings
   SQL_AUTH=sql        # "windows" or "sql"
   SQL_SERVER=your_sql_server
   SQL_DATABASE=your_database
   SQL_USER=sa          # only for SQL auth
   SQL_PASS=            # only for SQL auth
   SQL_TABLE=historical_data
   ```

3. **Run the Windows installer** by double-clicking **`launch.bat`** or from PowerShell:

   ```powershell
   .\launch.bat
   ```

   This script will:

   * Create and activate a Python virtual environment (`venv`)
   * Install dependencies: `paho-mqtt`, `influxdb-client`, `pyodbc`, `flask`, `psutil`
   * Launch the Flask dashboard on port 5050

---

## 📂 `launch.bat` Installer Script

```bat
@echo off
REM === Robo Data Dashboard Installer ===

REM 1. Create and activate venv
python -m venv venv
call venv\Scripts\activate

echo Installing dependencies...
%venv%\Scripts\pip install --upgrade pip
%venv%\Scripts\pip install paho-mqtt influxdb-client pyodbc flask psutil

echo Launching dashboard...
start "" cmd /k "%venv%\Scripts\python Tele_Robo_Bridge.py"

pause
```

---

## 🎬 Usage

1. **Edit** `config.txt` with your settings.
2. **Launch** the dashboard via `launch.bat`.
3. **Browser** opens automatically at `http://127.0.0.1:5050/`.
4. **Monitor** the bridge status and device last-seen timestamps.
5. **Click** the "Run MQTT Bridge" button to start or restart the data bridge.

---

## 🛠 Project Structure

```
Robo-replicate-data-dashboard/
├── mqtt_bridge_sql_influx.py   # MQTT → InfluxDB + SQL bridge
├── Tele_Robo_Bridge.py         # Flask dashboard & launcher
├── config.txt                  # All connection settings
├── launch.bat                  # Windows installer & launcher
└── static/
    └── logo.png               # Dashboard logo
```

---

## 📄 License

MIT License

Copyright (c) 2025 Jose Perez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
