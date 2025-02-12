# ----------------------------------------------------------------------------
# main.py
# Runs a simple interface to interact with the scanner via USB
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
import socket
import time
from driver.servo import Servo
import board

# Initialize servos
servoPAN = Servo(board.SERVO_PAN, us_range=board.PAN_RANGE_US, ang_range=board.PAN_RANGE_DEG)
servoTLT = Servo(board.SERVO_TLT, us_range=board.TLT_RANGE_US, ang_range=board.TLT_RANGE_DEG)

last_angle_pan = 0
last_angle_tlt = 0

def smooth_move(servo, current_angle, target_angle, step=2, delay=0.05):
    """Move servo smoothly from current_angle to target_angle."""
    step = step if target_angle > current_angle else -step
    for angle in range(current_angle, target_angle + step, step):
        servo.angle = angle
        time.sleep(delay)
    servo.angle = target_angle
    return target_angle

def move_to(target_PAN, target_TLT, step=2, delay=0.05):
    """Move both servos smoothly to target positions."""
    global last_angle_pan, last_angle_tlt
    last_angle_pan = smooth_move(servoPAN, last_angle_pan, target_PAN, step, delay)
    last_angle_tlt = smooth_move(servoTLT, last_angle_tlt, target_TLT, step, delay)
    return "Moved to PAN={}, TILT={}".format(last_angle_pan,last_angle_tlt)
# Send response back

# Start TCP Server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', 12345))  # Listen on port 12345
server.listen(1)
print("ESP32 Servo Control Ready. Waiting for connections...")

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
                print("Received Command: MOVE to PAN={}, TILT={}".format(pan_angle,tilt_angle))
                
                # Execute move and send response
                response = move_to(pan_angle, tilt_angle)
                conn.sendall(response.encode() + b"\n")  # Send status back
            except Exception as e:
                conn.sendall("ERROR: {}\n".format(str(e)).encode())  # Send error response
    conn.close()
