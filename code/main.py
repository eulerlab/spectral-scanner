# ----------------------------------------------------------------------------
# main.py
# Runs a simple interface to interact with the scanner via USB
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
# ----------------------------------------------------------------------------
import time
from machine import UART

# ----------------------------------------------------------------------------
def main():

  uart = UART(0, 9600)
  # Loop ...
  print("Entering loop ...")
  try:
    try:
      round = 0

      while True:
        try:
          if uart.any():
            ln = uart.readline()
            print(round, ln)

        finally:
          # ...
          time.sleep_ms(200)
          round += 1

    except KeyboardInterrupt:
      print("Loop stopped.")

  finally:
    # ...
    print("Done")

# ----------------------------------------------------------------------------

# Call main
if __name__ == "__main__":
  pass
  #main()

# ----------------------------------------------------------------------------
