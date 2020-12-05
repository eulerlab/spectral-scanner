# ----------------------------------------------------------------------------
# wlan.py
# Function to connect to the local WLAN
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
# ----------------------------------------------------------------------------
import network
import time
from NETWORK import my_ssid, my_wp2_pwd

# ----------------------------------------------------------------------------
def connect(led_func=None):
  """ Connect to WLAN if not already connected
  """
  if network.WLAN(network.STA_IF).isconnected():
    print("Already connected.")
  else:
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
      print("Connecting to network...")
      sta_if.active(True)
      sta_if.connect(my_ssid, my_wp2_pwd)
      n = 300
      while not sta_if.isconnected() and n > 0:
        if led_func:
          led_func.on()
        time.sleep(0.05)
        if led_func:
          led_func.off()
        time.sleep(0.05)
        n -= 1
      if sta_if.isconnected():
        print("[{0:>12}] {1}".format("network", sta_if.ifconfig()))
      else:
        print("ERROR: Could not connect to `{0}`".format(my_ssid))

def disconnect():
  """ Disconnect from WLAN
  """
  if not network.WLAN(network.STA_IF).isconnected():
    print("Not connected.")
  else:
    network.WLAN(network.STA_IF).disconnect()
    print("Disconnected.")

# ----------------------------------------------------------------------------
def syncDateTime(datetime=None, ntp_server="0.de.pool.ntp.org"):
  """ Synchronize with a time server, if connected
      `datetime` is a tuple with `(year, month, day, weekday, hours, minutes,
       seconds, subseconds)` and weekday 1-7 for Monday through Sunday.
  """
  from machine import RTC
  rtc = RTC()
  if datetime:
    rtc.datetime(datetime)
  elif not network.WLAN(network.STA_IF).isconnected():
    print("ERROR: Could not synchronize because not connected to WLAN")
    return
  else:
    import ntptime
    if len(ntp_server) > 0:
      ntptime.server = ntp_server
    ntptime.settime()
  t = rtc.datetime()
  print("RTC set to {0}, {1}.{2}.{3}, {4}:{5}"
        .format(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][t[3]],
                t[2], t[1], t[0], t[4], t[5]))


# ----------------------------------------------------------------------------
