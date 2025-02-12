# ----------------------------------------------------------------------------
# boot.py
# Runs at startup
#
# The MIT License (MIT)
# Copyright (c) 2025 Yuyao Deng
# 2025-02-12, v2
# --------
import network
import time

#SSID ='jd'#
SSID = "Speedy"
# PASSWORD = 'dengyuyaoABCD'#
PASSWORD = "1821...&%"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

if not wifi.isconnected():
    print("Connecting to Wi-Fi...")
    wifi.connect(SSID, PASSWORD)
    
    # Wait until connected
    while not wifi.isconnected():
        time.sleep(1)

print("Connected to Wi-Fi:", wifi.ifconfig())  # Show IP Address
