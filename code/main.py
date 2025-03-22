# ----------------------------------------------------------------------------
# main.py
# Runs a simple interface to interact with the scanner via USB
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
print("main.py started automatically")

import socket
import time
import network
from driver.servo import Servo
import board

def announce_ip_handshake(to_ip="192.168.2.255", port=8266, timeout=20):
    import socket
    start = time.time()
    my_ip = wifi.ifconfig()[0]
    msg = "I_AM_ESP32:{}".format(my_ip)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.settimeout(1)  # 1 sec listen timeout

    print("Starting handshake broadcast...")

    while time.time() - start < timeout:
        # Send the announcement
        udp.sendto(msg.encode(), (to_ip, port))
        print("Sent:", msg)
        try:
            # Wait for ACK
            data, addr = udp.recvfrom(1024)
            if data.decode().strip() == "GOT_IP":
                print("Handshake received from", addr)
                break
        except:
            pass
        time.sleep(2)
    udp.close()


# Wait for Wi-Fi to be connected
wifi = network.WLAN(network.STA_IF)
print("Waiting for Wi-Fi...", end="")
for _ in range(20):  # Wait max 10 seconds
    if wifi.isconnected():
        print(" connected!")
        announce_ip_handshake()
        break
    print(".", end="")
    time.sleep(0.5)
else:
    print("\n❌ Wi-Fi not connected — aborting.")
    raise SystemExit

# Initialize servos
servoPAN = Servo(board.SERVO_PAN, us_range=board.PAN_RANGE_US, ang_range=board.PAN_RANGE_DEG)
servoTLT = Servo(board.SERVO_TLT, us_range=board.TLT_RANGE_US, ang_range=board.TLT_RANGE_DEG)

last_angle_pan = 0
last_angle_tlt = 0

def smooth_move(servo, current_angle, target_angle, step=2, delay=0.05):
    step = step if target_angle > current_angle else -step
    for angle in range(current_angle, target_angle + step, step):
        servo.angle = angle
        time.sleep(delay)
    servo.angle = target_angle
    return target_angle

def move_to(target_PAN, target_TLT, step=2, delay=0.05):
    global last_angle_pan, last_angle_tlt
    last_angle_pan = smooth_move(servoPAN, last_angle_pan, target_PAN, step, delay)
    last_angle_tlt = smooth_move(servoTLT, last_angle_tlt, target_TLT, step, delay)
    return "Moved to PAN={}, TILT={}".format(last_angle_pan, last_angle_tlt)



# Start TCP Server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', 12345))
server.listen(1)

print("ESP32 Servo Control Ready. IP:", wifi.ifconfig()[0])
print("Waiting for connections...")

while True:
    conn, addr = server.accept()
    print("Client connected:", addr)
    while True:
        data = conn.recv(1024)
        if not data:
            break
        command = data.decode().strip()
        if command.startswith("MOVE:"):
            try:
                parts = command.split(":")[1].split(",")
                pan_angle = int(parts[0])
                tilt_angle = int(parts[1])
                print("MOVE to PAN={}, TILT={}".format(pan_angle, tilt_angle))
                response = move_to(pan_angle, tilt_angle)
                conn.sendall(response.encode() + b"\n")
            except Exception as e:
                conn.sendall("ERROR: {}\n".format(str(e)).encode())
    conn.close()
