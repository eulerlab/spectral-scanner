import time
import board
from driver.servo import Servo

servoPan = Servo(board.SERVO_PAN, us_range=board.PAN_RANGE_US,
                 ang_range=board.PAN_RANGE_DEG, verbose=True)

servoPan.angle = 0
time.sleep_ms(1000)
servoPan.angle = 60
time.sleep_ms(1000)
servoPan.angle = -60
time.sleep_ms(1000)
servoPan.angle = 0
