import time
import board
from driver.busio import I2CBus
from driver.compass_cmps12 import Compass

try:
  i2c = I2CBus(board.I2C_FRQ, board.SCL, board.SDA, code=0)
  compass = Compass(i2c)
  for i in range(100):
    print(compass.getHeading3D())
    time.sleep_ms(1000)
finally:
  i2c.deinit()
