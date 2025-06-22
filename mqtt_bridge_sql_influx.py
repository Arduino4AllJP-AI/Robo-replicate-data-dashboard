import os
import json
import time
import csv
import paho.mqtt.client as mqtt
import pyodbc
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# === Load config from file ===
def load_config(path="config.txt"):
    config = {}
    with open(path, "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.strip().split("=", 1)
                config[key] = val
    return config

config = load_config()

# === InfluxDB Setup ===
write_api = None
if config.get("INFLUX_URL"):
    influx_client = InfluxDBClient(
        url   = config["INFLUX_URL"],
        token = config["INFLUX_TOKEN"],
        org   = config["INFLUX_ORG"]
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("✅ Connected to InfluxDB.")

# === SQL Server Setup ===
conn_sql = None
try:
    if config.get("SQL_AUTH", "windows").lower() == "windows":
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config['SQL_SERVER']};"
            f"DATABASE={config['SQL_DATABASE']};"
            "Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config['SQL_SERVER']};"
            f"DATABASE={config['SQL_DATABASE']};"
            f"UID={config['SQL_USER']};"
            f"PWD={config['SQL_PASS']};"
        )
    conn_sql  = pyodbc.connect(conn_str)
    cursor_sql = conn_sql.cursor()
    print("✅ Connected to SQL Server.")
except Exception as e:
    print(f"❌ Failed to connect to SQL Server: {e}")
    print("⚠️ Will continue running without SQL logging.")

# === MQTT Callback ===
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print("⚠️ Failed to parse JSON:", e)
        return

    print("Received:", data)

    # 1) InfluxDB write (errors here won’t stop SQL)
    if write_api:
        try:
            point = (
                Point("fielddevices")
                .tag("device", data.get("DEV_EUI", "unknown"))
                .field("value", float(data.get("Water level", 0)))
                .time(data.get("TIMESTAMP"))
            )
            write_api.write(
                bucket = config["INFLUX_BUCKET"],
                org    = config["INFLUX_ORG"],
                record = point
            )
        except Exception as e:
            print("⚠️ Influx write failed:", e)

    # 2) SQL write
    if conn_sql:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            json_blob = json.dumps(data)

            # keep only latest 100 rows
            cursor_sql.execute(f"SELECT COUNT(*) FROM {config['SQL_TABLE']}")
            row_count = cursor_sql.fetchone()[0]

            if row_count < 100:
                cursor_sql.execute(
                    f"INSERT INTO {config['SQL_TABLE']} (timestamp, json_data) VALUES (?, ?)",
                    timestamp, json_blob
                )
            else:
                cursor_sql.execute(
                    f"SELECT TOP 1 id FROM {config['SQL_TABLE']} ORDER BY timestamp ASC"
                )
                oldest_id = cursor_sql.fetchone()[0]
                cursor_sql.execute(
                    f"UPDATE {config['SQL_TABLE']} SET timestamp=?, json_data=? WHERE id=?",
                    timestamp, json_blob, oldest_id
                )

            conn_sql.commit()

            # Export the latest 100 records to CSV
            cursor_sql.execute(
                f"SELECT TOP 100 * FROM {config['SQL_TABLE']} ORDER BY timestamp DESC"
            )
            rows = cursor_sql.fetchall()
            with open("historical_data.csv", "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                # header
                writer.writerow([col[0] for col in cursor_sql.description])
                # data
                writer.writerows(rows)

        except Exception as e:
            print("⚠️ SQL write failed:", e)

# === MQTT Setup ===
client = mqtt.Client()
if config.get("MQTT_USERNAME") and config.get("MQTT_PASSWORD"):
    client.username_pw_set(config["MQTT_USERNAME"], config["MQTT_PASSWORD"])
client.tls_set()
client.on_message = on_message

# === Connect & Subscribe ===
while True:
    try:
        client.connect(config["MQTT_BROKER"], int(config["MQTT_PORT"]))
        print("✅ Connected to MQTT broker.")
        break
    except Exception as e:
        print(f"❌ Failed to connect to MQTT broker: {e}")
        print("🔁 Retrying in 10 seconds...")
        time.sleep(10)

client.subscribe(config["MQTT_TOPIC"])
print("📡 Listening for MQTT → InfluxDB + SQL Server...")
client.loop_forever()
