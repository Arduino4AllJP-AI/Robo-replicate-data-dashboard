import os
import json
import time
import paho.mqtt.client as mqtt
import pyodbc
import csv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# === Load config from file ===
def load_config(path="config.txt"):
    config = {}
    with open(path, "r") as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                config[key.strip()] = val.strip()
    return config

config = load_config()

# === InfluxDB Setup ===
write_api = None
try:
    influx = InfluxDBClient(
        url=config["INFLUX_URL"],
        token=config["INFLUX_TOKEN"],
        org=config["INFLUX_ORG"]
    )
    write_api = influx.write_api(write_options=SYNCHRONOUS)
except Exception as e:
    print(f"❌ Failed to connect to InfluxDB: {e}")
    print("⚠️ Will continue running without InfluxDB.")

# === SQL Server Setup ===
conn_sql = None
try:
    if config.get("SQL_AUTH", "windows").lower() == "windows":
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={config['SQL_SERVER']};DATABASE={config['SQL_DATABASE']};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={config['SQL_SERVER']};DATABASE={config['SQL_DATABASE']};UID={config['SQL_USER']};PWD={config['SQL_PASS']};"
    conn_sql = pyodbc.connect(conn_str)
    cursor_sql = conn_sql.cursor()
    print("✅ Connected to SQL Server.")
except Exception as e:
    print(f"❌ Failed to connect to SQL Server: {e}")
    print("⚠️ Will continue running without SQL logging.")

# === MQTT Callback ===
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print("Received:", data)

        # Write to InfluxDB
        if write_api:
            point = (
                Point("fielddevices")
                .tag("device", data.get("device", "unknown"))
                .field("millis", int(data.get("millis", 0)))
                .field("message", str(data.get("message", "")))
            )
            write_api.write(bucket=config["INFLUX_BUCKET"], org=config["INFLUX_ORG"], record=point)

        # Write to SQL Server with circular overwrite
        if conn_sql:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            json_data = json.dumps(data)

            cursor_sql.execute(f"SELECT COUNT(*) FROM {config['SQL_TABLE']}")
            row_count = cursor_sql.fetchone()[0]

            if row_count < 100:
                cursor_sql.execute(
                    f"INSERT INTO {config['SQL_TABLE']} (timestamp, json_data) VALUES (?, ?)",
                    timestamp, json_data
                )
            else:
                cursor_sql.execute(
                    f"SELECT TOP 1 id FROM {config['SQL_TABLE']} ORDER BY timestamp ASC"
                )
                oldest_id = cursor_sql.fetchone()[0]
                cursor_sql.execute(
                    f"UPDATE {config['SQL_TABLE']} SET timestamp = ?, json_data = ? WHERE id = ?",
                    timestamp, json_data, oldest_id
                )
            conn_sql.commit()

            # Export latest 100 records to CSV
            cursor_sql.execute(f"SELECT TOP 100 * FROM {config['SQL_TABLE']} ORDER BY timestamp DESC")
            rows = cursor_sql.fetchall()
            with open("historical_data.csv", "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([column[0] for column in cursor_sql.description])  # headers
                writer.writerows(rows)

    except Exception as e:
        print("⚠️ Error processing message:", e)

# === MQTT Setup ===
client = mqtt.Client()
if "MQTT_USERNAME" in config and "MQTT_PASSWORD" in config:
    client.username_pw_set(config["MQTT_USERNAME"], config["MQTT_PASSWORD"])
client.tls_set()

# === MQTT Connection Retry ===
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
client.on_message = on_message

print("📡 Listening for MQTT → InfluxDB + SQL Server...")
client.loop_forever()