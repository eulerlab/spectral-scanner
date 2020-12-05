# ----------------------------------------------------------------------------
# busio.py
#
# Basic bus support
# (for standard micropython, ESP32, as HUZZAH32 feather)
#
# The MIT License (MIT)
# Copyright (c) 2018 Thomas Euler
# 2018-09-21, v1
# 2019-12-21, v1.1 - hardware I2C bus possible
# 2020-08-09, v1.2 - `UART` is inherited from `machine`
# 2020-10-09, v1.3 - `I2CBus` use with `with`-statement
# ----------------------------------------------------------------------------
from os import uname
from machine import SPI, Pin, I2C
from micropython import const
from machine import UART

__version__ = "0.1.2.0"

# ----------------------------------------------------------------------------
class SPIBus(object):
  """SPI bus access."""

  def __init__(self, freq, sc, mo, mi=None, spidev=2):
    self._spi = SPI(spidev)
    if mi == None:
      self._spi.init(baudrate=freq, sck=Pin(sc), mosi=Pin(mo))
    else:
      self._spi.init(baudrate=freq, sck=Pin(sc), mosi=Pin(mo), miso=Pin(mi))

  def deinit(self):
    self._spi.deinit()

  @property
  def bus(self):
    return self._spi

  def write_readinto(self, wbuf, rbuf):
    self._spi.write_readinto(wbuf, rbuf)

  def write(self, wbuf):
    self._spi.write(wbuf)

# ----------------------------------------------------------------------------
class I2CBus(object):
  """I2C bus access."""

  def __init__(self, _freq, scl, sda, code=-1):
    self._i2cDevList = []
    if not code in [-1,0,1] or float(uname()[2][:4]) < 1.12:
      # Defaults to software implementation of I2C
      self._i2c = I2C(scl=Pin(scl), sda=Pin(sda), freq=_freq)
      self._isSoft = True
      codeStr = "Software"
    else:
      # User selected -1=software or 0,1=hardware implementation of I2C
      self._i2c = I2C(code, scl=Pin(scl), sda=Pin(sda), freq=_freq)
      self._isSoft = True if code == -1 else False
      codeStr = "Software" if self._isSoft else "Hardware #{0}".format(code)
    print("{0} I2C bus frequency is {1} kHz".format(codeStr, _freq/1000))
    print("Scanning I2C bus ...")
    self._i2cDevList = self._i2c.scan()
    print("... {0} device(s) found ({1})"
          .format(len(self._i2cDevList), self._i2cDevList))

  def deinit(self):
    self._i2c = None

  @property
  def bus(self):
    return self._i2c

  @property
  def deviceAddrList(self):
    return self._i2cDevList

  def start(self):
    assert self._isSoft, "SoftI2C expected"
    self._i2c.start()

  def stop(self):
    assert self._isSoft, "SoftI2C expected"
    self._i2c.stop()

  def write(self, buf):
    assert self._isSoft, "SoftI2C expected"
    self._i2c.write(buf)

  def writeto(self, addr, buf, stop_=True):
    self._i2c.writeto(addr, buf, stop_)

  def readinto(self, buf):
    self._i2c.readinto(buf)

  def readfrom(self, addr):
    return self._i2c.readfrom(addr)

  def readfrom_into(self, addr, buf):
    self._i2c.readfrom_into(addr, buf)

  def write_then_readinto(self, addr, bufo, bufi, out_start=0, out_end=None,
                          in_start=0, in_end=None, stop_=True):
    self._i2c.writeto(addr, bufo[out_start:out_end], stop_)
    buf = bytearray(bufi[in_start:in_end])
    self._i2c.readfrom_into(addr, buf)
    bufi[in_start:in_end] = buf

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    return False

# ----------------------------------------------------------------------------
