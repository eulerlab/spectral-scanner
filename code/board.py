# ----------------------------------------------------------------------------
# board.py
# Pin definitions
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
# ----------------------------------------------------------------------------
from micropython import const

# Spectrometer (CM12880MA)
TRG            = const(14)
STA            = const(15)
CLK            = const(21)
VID            = const(36)

# I2C for compass etc.
SDA            = const(23)
SCL            = const(22)
I2C_FRQ        = const(400000)

# Serial for extensions
TX             = const(17)
RX             = const(16)

# Servos
SERVO_PAN      = const(27)
PAN_RANGE_US   = [1010, 1931]
PAN_RANGE_DEG  = [-45, 45]
SERVO_TLT      = const(33)
TLT_RANGE_US   = [1033, 1916]
TLT_RANGE_DEG  = [-45, 45]

# NeoPixel
NEOPIX         = const(32)

# ----------------------------------------------------------------------------
