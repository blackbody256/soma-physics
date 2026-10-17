"""Usage: python qr.py <ssid> <password> <laptop-ip>
Example: python qr.py PhysicsTutor tutor2026 192.168.137.1"""
import sys

import qrcode

ssid, password, ip = sys.argv[1:4]
qrcode.make(f"WIFI:T:WPA;S:{ssid};P:{password};;").save("qr_wifi.png")
qrcode.make(f"http://{ip}:8000").save("qr_app.png")
print("Saved qr_wifi.png and qr_app.png")
