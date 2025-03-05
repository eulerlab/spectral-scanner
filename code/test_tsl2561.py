from driver.tsl2561 import TSL2561
from machine import I2C, Pin

# Initialize I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(23), freq=400000)

# Initialize the sensor
sensor= TSL2561(i2c)  # Address 0x39 (57 in decimal)

# Read light intensity
lux2 = sensor.read()
# print("Light Intensity:", lux, "lux")
print(lux2)

