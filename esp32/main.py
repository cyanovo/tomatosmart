'''
uart0  uart1(232)  uart2(485)
'''
from umqtt.simple import MQTTClient
import machine, ustruct, ujson
import utime
import network
from machine import Pin
import time
import uasyncio as asyncio
import usocket as socket

# ========== 硬件初始化 ==========
DO1 = Pin(15, Pin.OUT)
DO2 = Pin(16, Pin.OUT)
DO1.value(0)
DO2.value(0)
uart = machine.UART(2, baudrate=115200, parity=None, stop=1)

# ========== 配置文件管理 ==========
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return ujson.load(f)
    except:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            ujson.dump(cfg, f)
        return True
    except Exception as e:
        print("save config error:", e)
        return False

_config = load_config()
ssid = _config.get("wifi_ssid", "ahao")
pwd = _config.get("wifi_pwd", "12345678")
server_url = _config.get("mqtt_server", "10.156.145.58")
user = _config.get("mqtt_user", "admin")
password = _config.get("mqtt_password", "admin123")

# ========== MQTT Topic ==========
get_strawberry_irrigation = "strawberry_irrigation"
get_strawberry_fan = "strawberry_fan"

# ========== AP 配网参数 ==========
AP_SSID = "A-strawberry"
AP_PWD = "12345678"

print("=" * 40)
print("Current Config:")
print("  WiFi SSID :", ssid)
print("  WiFi PWD  :", pwd)
print("  MQTT IP   :", server_url)
print("  AP SSID   :", AP_SSID)
print("  AP PWD    :", AP_PWD)
print("=" * 40)

# ========== 连接状态标志 ==========
wifi_connected = False
mqtt_connected = False
last_reconnect_attempt = 0
reconnect_interval = 10000


# ========== WiFi 连接 ==========
async def async_connect_wifi():
    """异步 WiFi 连接，不阻塞事件循环"""
    global wifi_connected
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.active(True)
        wlan.disconnect()  # 清除可能卡住的旧连接状态
        await asyncio.sleep(0.5)

        if not wlan.isconnected():
            print("connecting WiFi...")
            wlan.connect(ssid, pwd)
            for _ in range(10):
                if wlan.isconnected():
                    break
                await asyncio.sleep(1)

        if wlan.isconnected():
            wifi_connected = True
            print("WiFi OK:", wlan.ifconfig())
            return True
        else:
            wifi_connected = False
            print("WiFi FAIL")
            return False
    except OSError as e:
        wifi_connected = False
        print("WiFi error:", e)
        return False

def connect_wifi():
    """同步版本，仅兼容旧调用"""
    global wifi_connected
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.active(True)
        wlan.disconnect()
        time.sleep(0.5)
        if not wlan.isconnected():
            wlan.connect(ssid, pwd)
            for _ in range(10):
                if wlan.isconnected():
                    break
                time.sleep(1)
        wifi_connected = wlan.isconnected()
        if wifi_connected:
            print("WiFi OK:", wlan.ifconfig())
        else:
            print("WiFi FAIL")
        return wifi_connected
    except OSError:
        wifi_connected = False
        return False

def check_wifi():
    global wifi_connected
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        wifi_connected = True
        return True
    wifi_connected = False
    return False

async def async_reconnect_wifi():
    global wifi_connected
    print("reconnect WiFi...")
    wifi_connected = await async_connect_wifi()
    return wifi_connected

def reconnect_wifi():
    global wifi_connected
    wifi_connected = connect_wifi()
    return wifi_connected


# ========== MQTT 连接 ==========
def mqtt_connect():
    global client, mqtt_connected
    try:
        client = MQTTClient(
            client_id="esp32-" + str(utime.ticks_ms()),
            server=server_url,
            user=user,
            port=1883,
            password=password,
            keepalive=60
        )
        client.set_callback(on_subcribe)
        client.connect()
        client.subscribe(get_strawberry_irrigation)
        client.subscribe(get_strawberry_fan)
        mqtt_connected = True
        print("MQTT OK")
        return True
    except Exception as e:
        mqtt_connected = False
        print("MQTT FAIL:", e)
        return False

def check_mqtt():
    global mqtt_connected, client
    try:
        client.ping()
        mqtt_connected = True
        return True
    except:
        mqtt_connected = False
        return False

def reconnect_mqtt():
    global mqtt_connected
    print("reconnect MQTT...")
    mqtt_connected = mqtt_connect()
    return mqtt_connected


# ========== 连接管理 ==========
async def check_and_reconnect():
    global last_reconnect_attempt, wifi_connected, mqtt_connected
    t = utime.ticks_ms()
    if utime.ticks_diff(t, last_reconnect_attempt) > reconnect_interval:
        last_reconnect_attempt = t
        if not check_wifi():
            print("WiFi lost, reconnecting...")
            if await async_reconnect_wifi():
                if not check_mqtt():
                    reconnect_mqtt()
            return False
        if not check_mqtt():
            print("MQTT lost, reconnecting...")
            reconnect_mqtt()
            return False
    return wifi_connected and mqtt_connected


# ========== MQTT 回调 ==========
def on_subcribe(topic, msg):
    try:
        payload = msg.decode() if isinstance(msg, bytes) else msg
        topic_str = topic.decode() if isinstance(topic, bytes) else topic
        print("topic:", topic_str, "payload:", payload)

        if topic_str == get_strawberry_irrigation:
            cloudmsg = ujson.loads(payload)
            action = cloudmsg.get("action", "")
            if action == "start":
                asyncio.create_task(relay_control_task(DO1, 300))
            else:
                DO1.value(0)

        elif topic_str == get_strawberry_fan:
            try:
                cloudmsg = ujson.loads(payload)
                action = cloudmsg.get("action", "")
                DO2.value(1) if action == "start" else DO2.value(0)
            except:
                if payload == "start":
                    DO2.value(1)
                elif payload == "stop":
                    DO2.value(0)
    except Exception as e:
        print("sub error:", e)


# ========== 继电器控制 ==========
async def relay_control_task(relay_pin, on_time_seconds):
    relay_pin.value(1)
    await asyncio.sleep(on_time_seconds)
    relay_pin.value(0)


# ========== 传感器数据采集 ==========
async def sensor_data_send(uart, s):
    if not wifi_connected or not mqtt_connected:
        return
    try:
        uart.write(bytes.fromhex(s))
        await asyncio.sleep_ms(500)
        raw_data = uart.read()

        if raw_data is None or len(raw_data) < 2:
            return

        addr = raw_data.hex()[:2]

        if addr == "01":
            r = raw_data[3:-2]
            humidity = ustruct.unpack(">H", r[0:2])[0] / 10.0
            temp = ustruct.unpack(">H", r[2:4])[0] / 10.0
            co2 = ustruct.unpack(">H", r[4:6])[0]
            illum = ustruct.unpack(">H", r[6:8])[0]
            client.publish("/air/post", ujson.dumps({
                "humidity": humidity, "temp": temp,
                "co2": co2, "Illumination": illum
            }))
            print("air  | temp:{:.1f}C hum:{:.1f}% co2:{}ppm illum:{}Lux".format(temp, humidity, co2, illum))

        elif addr == "02":
            if len(raw_data) < 19:
                return
            r = raw_data[3:-2]
            sm = ustruct.unpack(">H", r[0:2])[0] / 10.0
            st = ustruct.unpack(">H", r[2:4])[0] / 10.0
            sc = ustruct.unpack(">H", r[4:6])[0]
            ph = ustruct.unpack(">H", r[6:8])[0] / 10.0
            n  = ustruct.unpack(">H", r[8:10])[0]
            p  = ustruct.unpack(">H", r[10:12])[0]
            k  = ustruct.unpack(">H", r[12:14])[0]
            client.publish("/soil/post", ujson.dumps({
                "soil_moisture": sm, "soil_temperature": st,
                "soil_conductivity": sc, "ph_value": ph,
                "nitrogen": n, "phosphorus": p, "potassium": k
            }))
            print("soil | moist:{:.1f}% temp:{:.1f}C ec:{} ph:{:.1f} N:{} P:{} K:{}".format(sm, st, sc, ph, n, p, k))

    except Exception as e:
        print("sensor error:", e)


# ============================================================
#        配网 Web 服务器（AP 常驻，与 STA 共存）
# ============================================================

def _config_html():
    return """HTTP/1.1 200 OK\r
Content-Type: text/html; charset=utf-8\r
Connection: close\r
\r
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Config</title>
<style>
body{{font-family:Arial;padding:20px;background:#f4f9f4;color:#333}}
.card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.1)}}
h2{{color:#2d6a4f;margin:0 0 12px}}
label{{display:block;font-size:14px;margin:12px 0 4px;color:#555}}
input{{width:100%;padding:10px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;font-size:15px}}
button{{width:100%;padding:12px;margin-top:16px;background:#40916c;color:#fff;border:none;border-radius:6px;font-size:16px}}
</style></head><body>
<div class="card">
<h2>Strawberry Config</h2>
<form method="post" action="/save">
<label>WiFi SSID</label>
<input name="ssid" value="{ssid}">
<label>WiFi Password</label>
<input name="pwd" value="{pwd}" type="password">
<label style="font-weight:bold;color:#2d6a4f">MQTT Server IP</label>
<input name="mqtt" value="{mqtt}" style="font-weight:bold;border-color:#40916c">
<label>MQTT User</label>
<input name="mqtt_user" value="{mqtt_user}">
<label>MQTT Password</label>
<input name="mqtt_pwd" value="{mqtt_pwd}" type="password">
<button type="submit">Save & Reboot</button>
</form>
</div></body></html>
""".format(
    ssid=_config.get("wifi_ssid", "ahao"),
    pwd=_config.get("wifi_pwd", "12345678"),
    mqtt=_config.get("mqtt_server", "10.156.145.58"),
    mqtt_user=_config.get("mqtt_user", "admin"),
    mqtt_pwd=_config.get("mqtt_password", "admin123")
)

def _ok_html():
    return """HTTP/1.1 200 OK\r
Content-Type: text/html; charset=utf-8\r
Connection: close\r
\r
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OK</title>
<style>body{{font-family:Arial;padding:40px;text-align:center;background:#f4f9f4}}
.card{{background:#fff;border-radius:12px;padding:30px}}
h2{{color:#2d6a4f}}</style></head><body>
<div class="card"><h2>Saved!</h2><p>Rebooting...</p></div>
</body></html>
"""

def _parse_form(body):
    params = {}
    try:
        for pair in body.split("&"):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            v = v.replace("+", " ")
            out = []
            i = 0
            while i < len(v):
                if v[i] == "%" and i + 2 < len(v):
                    out.append(chr(int(v[i+1:i+3], 16)))
                    i += 3
                else:
                    out.append(v[i])
                    i += 1
            params[k] = "".join(out)
    except:
        pass
    return params

async def _handle_http(conn):
    try:
        req = b""
        # 读取直到 \r\n\r\n（header 结束）
        for _ in range(30):
            try:
                chunk = conn.recv(256)
                if chunk:
                    req += chunk
                    if b"\r\n\r\n" in req:
                        break
            except OSError:
                pass
            await asyncio.sleep_ms(100)
        if not req:
            return

        s = req.decode("utf-8", "ignore")
        line1 = s.split("\r\n")[0]
        parts = line1.split(" ")
        method = parts[0] if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        # POST 请求需要读取 body
        body = ""
        if method == "POST":
            # 解析 Content-Length
            cl = 0
            for line in s.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    cl = int(line.split(":")[1].strip())
                    break
            # 已读 body 部分
            if "\r\n\r\n" in s:
                body = s.split("\r\n\r\n", 1)[-1]
            # 补读剩余 body
            while len(body.encode()) < cl:
                try:
                    chunk = conn.recv(256)
                    if chunk:
                        req += chunk
                        body += chunk.decode("utf-8", "ignore")
                    else:
                        break
                except OSError:
                    pass
                await asyncio.sleep_ms(100)

        if method == "GET" and (path == "/" or path == "/index.html"):
            conn.send(_config_html().encode("utf-8"))

        elif method == "POST" and path == "/save":
            p = _parse_form(body)
            if p:
                _config["wifi_ssid"] = p.get("ssid", _config.get("wifi_ssid", ""))
                _config["wifi_pwd"] = p.get("pwd", _config.get("wifi_pwd", ""))
                _config["mqtt_server"] = p.get("mqtt", _config.get("mqtt_server", ""))
                _config["mqtt_user"] = p.get("mqtt_user", _config.get("mqtt_user", ""))
                _config["mqtt_password"] = p.get("mqtt_pwd", _config.get("mqtt_password", ""))
                save_config(_config)
            conn.send(_ok_html().encode("utf-8"))
            await asyncio.sleep(2)
            machine.reset()

        else:
            conn.send(b"HTTP/1.1 302 Found\r\nLocation: /\r\nConnection: close\r\n\r\n")
    except Exception as e:
        print("http err:", e)
    finally:
        try:
            conn.close()
        except:
            pass

async def config_web_server():
    """AP mode web server for changing IP"""
    # 暂时关闭 STA，释放射频给 AP 广播
    _sta = network.WLAN(network.STA_IF)
    _sta.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    time.sleep(0.5)
    try:
        ap.config(essid=AP_SSID, password=AP_PWD)
    except:
        ap.config(essid=AP_SSID)
    time.sleep(0.5)
    ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
    print("AP: {} -> {}".format(AP_SSID, ap.ifconfig()))
    print("Config page: http://192.168.4.1")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except:
        pass
    # 重试 bind，等 AP 网卡就绪
    for _ in range(5):
        try:
            s.bind(("0.0.0.0", 80))
            break
        except:
            time.sleep(0.5)
    s.listen(3)
    s.setblocking(False)
    print("Web server started")

    while True:
        try:
            conn, _ = s.accept()
            asyncio.create_task(_handle_http(conn))
        except OSError:
            pass
        await asyncio.sleep_ms(200)


# ========== 主程序 ==========
async def async_wifi_connect():
    """异步 WiFi + MQTT 连接，不阻塞事件循环"""
    global wifi_connected, mqtt_connected
    await asyncio.sleep(3)  # 等 AP 完全稳定
    wifi_connected = await async_connect_wifi()
    if wifi_connected:
        mqtt_connected = mqtt_connect()

def init():
    """同步版本，保留兼容"""
    global wifi_connected, mqtt_connected
    wifi_connected = connect_wifi()
    if wifi_connected:
        mqtt_connected = mqtt_connect()

async def main_loop():
    # AP + Web Server 第一时间启动，WiFi 断网也能立马配网
    asyncio.create_task(config_web_server())
    asyncio.create_task(client_check_msg_loop())
    # WiFi/MQTT 异步连接，不阻塞事件循环
    asyncio.create_task(async_wifi_connect())
    while True:
        try:
            if await check_and_reconnect():
                await sensor_data_send(uart, "01030000000585C9")
                await sensor_data_send(uart, "020300000007043B")
            await asyncio.sleep(5)
        except Exception as e:
            print("loop error:", e)
            await asyncio.sleep(10)

async def client_check_msg_loop():
    global client
    while True:
        try:
            if await check_and_reconnect():
                client.check_msg()
            await asyncio.sleep(1)
        except Exception as e:
            print("check_msg error:", e)
            await asyncio.sleep(10)

def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("stopped by user")
        DO1.value(0)
        DO2.value(0)
    except Exception as e:
        print("fatal:", e)
        machine.reset()

if __name__ == "__main__":
    main()
