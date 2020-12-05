# ----------------------------------------------------------------------------
# c12880ma.py
# Class for C12880MA spectrometer (Hamamatsu) breakout

# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-07, v1
# ----------------------------------------------------------------------------
import array
from micropython import const
from machine import Pin, ADC
from time import sleep_us, ticks_us, ticks_diff

__version__ = "0.1.0.0"
CHIP_NAME   = "C12880MA"
CHAN_COUNT  = const(288)
DELAY_US    = const(1)

# ----------------------------------------------------------------------------
class C12880MA(object):
  """Driver for for C12880MA spectrometer (Hamamatsu) breakout."""

  def __init__(self, trg, st, clk, video, led=None, laser=None):
    """ Initialises the pins that are connected to the breakout
    """
    # Initialize variables
    self._min_integ_us = 0
    self._integ_s = 0.

    # Initialize pins
    self._pinTrg = Pin(trg, Pin.OUT)
    self._pinSt = Pin(st, Pin.OUT)
    self._pinClk = Pin(clk, Pin.OUT)
    self._pinLED = Pin(led, Pin.OUT) if led else None
    self._pinLaser = Pin(laser, Pin.OUT) if laser else None

    # AIn for video input
    self._pinVideo = ADC(Pin(video))
    self._bit_depth = ADC.WIDTH_12BIT
    self._pinVideo.atten(ADC.ATTN_11DB)
    self._pinVideo.width(self._bit_depth)
    self._max_adc = 2**(9 +self._bit_depth) -1
    self.setIntegrationTime_s(0.001)

    # Array for spectral data
    self._nChan = CHAN_COUNT
    self._data = array.array("i", [0]*CHAN_COUNT)
    self._tmgs = array.array("i", [0]*5)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def begin(self):
    """ Start
    """
    # Initialize sensor
    self._pinClk.value(0)
    self._pinSt.value(0)
    self._measureMinIntegTime()

  def setIntegrationTime_s(self, t_s):
    self._integ_s = max(t_s, 0.)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def read(self):
    """ Read spectrometer data
    """
    # Calculate integration time
    tmgs = array.array("i", [0]*5)
    data = array.array("i", [0]*CHAN_COUNT)
    d_us = int(max(self._integ_s *1E6 -self._min_integ_us, 0))

    # Start clock cycle and set start pulse to signal start
    self._pinClk.value(1)
    sleep_us(DELAY_US)
    self._pinClk.value(0)
    self._pinSt.value(1)
    sleep_us(DELAY_US)

    # Pixel integration starts after three clock pulses
    self._pulseClock(3)
    tmgs[0] = ticks_us()

    # Integrate pixels for a while
    self._pulseClockTimed(d_us)

    # Set _ST_pin to low
    self._pinSt.value(0)
    tmgs[1] = ticks_us()

    # Sample for a period of time; integration stops at pulse 48-th pulse
    # after ST went low
    self._pulseClock(48)
    tmgs[2] = ticks_us()

    # Pixel output is ready after last pulse #88 after ST went low
    self._pulseClock(40)
    tmgs[3] = ticks_us()

    # Read from SPEC_VIDEO
    for i in range(CHAN_COUNT):
      data[i] = self._pinVideo.read()
      self._pulseClock(1)
    tmgs[4] = ticks_us()

    # Save data
    self._data = array.array("i", data)
    self._tmgs = array.array("i", tmgs)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  @property
  def channels(self):
    return CHAN_COUNT

  @property
  def spectrum(self):
    return self._data

  @property
  def wavelengths(self):
    A0 = 3.152446842e+2
    B1 = 2.688494791
    B2 = -8.964262020e-4
    B3 = -1.030880174e-5
    B4 = 2.083514791e-8
    B5 = -1.290505933e-11
    cl = lambda x: A0 +B1*x +B2*x**2 +B3*x**3 +B4*x**4 +B5*x**5
    nm = [int(cl(i+1.)) for i in range(CHAN_COUNT)]
    return array.array("f", nm)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _pulseClock(self, n_cycl):
    """ Pulse clock for `n_cycl` cycles
    """
    for i in range(n_cycl):
      self._pinClk.value(1)
      sleep_us(DELAY_US)
      self._pinClk.value(0)
      sleep_us(DELAY_US)

  def _pulseClockTimed(self, dur_ms):
    """ Pulse clock for `dur_ms` milliseconds
    """
    start = ticks_us()
    while ticks_diff(ticks_us(), start) < dur_ms:
      self._pinClk.value(1)
      sleep_us(DELAY_US)
      self._pinClk.value(0)
      sleep_us(DELAY_US)

  def _measureMinIntegTime(self):
    start = ticks_us()
    self._pulseClock(48)
    self._min_integ_us = ticks_diff(ticks_us(), start)

# ----------------------------------------------------------------------------
