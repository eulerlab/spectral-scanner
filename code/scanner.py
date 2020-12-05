# ----------------------------------------------------------------------------
# scanner.py
# Scanner class for taking spectral pictures
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-11-21, v1
# ----------------------------------------------------------------------------
import time
import board
import array
import ulab as np
import os
from machine import RTC
from micropython import const
from driver.servo import Servo
from driver.servo_manager import ServoManager
from driver.c12880ma import C12880MA

__version__      = "0.1.0.0"
__file_version__ = const(1)

# ----------------------------------------------------------------------------
class SpectImg(object):
  """Container class of a spectral image with all meta information
  """
  def __init__(self, size_xy, step_xy, int_s, n_spect, fname, overwrite=True):
    """ Create image of dimensions `size_xy` steps, with each pixel a spectrum
        of `n_spect` data points. Note that for simplicity, all image
        elements are kept as linear arrays (lines concatenated). Because of
        the limited RAM, the picture is kept in a file on the flash.
    """
    self.dXY = size_xy
    self.nPix = self.dXY[0] *self.dXY[1]
    self.stepXY = step_xy
    self.nSpect = n_spect
    self.tInt_s = int_s
    self._fname = fname
    self._file = None
    self._doOverwr = overwrite
    self._isReady = False
    self._lf = "\r\n"
    self._rtc = RTC()
    self._toSerial = None
    self._nPixStored = 0

    # Check if file exists and recreate it, if needed
    try:
      os.stat(self._fname)
      if not self._doOverwr:
        print("ERROR: `{0}` already exists and `overwrite=False`")
        return
      os.remove(self._fname)
    except OSError:
      pass
    print("Opening file `{0}`".format(self._fname))
    self._file = open(self._fname, "w")

    # Write header
    d = {"file_version": __file_version__}
    self._writeline("h,0", str(d))
    t = self._rtc.datetime()
    self._date = (t[0], t[1], t[2])
    self._time = (t[4], t[5], t[6])
    d = {"date_yyyymmdd": self._date, "time_hhmmss": self._time}
    self._writeline("h,1", str(d))
    d = {"size_xy": self.dXY, "step_xy_deg": self.stepXY,
         "n_spect": self.nSpect, "t_int_s": self.tInt_s}
    self._writeline("h,2", str(d))
    self._isReady = True

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  @property
  def onToSerial(self, f):
    self._toSerial = f

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def storePixel(self, xy, head, pitch, roll, spect):
    """ Store a pixel
    """
    pre = "p,{0}".format(self._nPixStored)
    d = {"xy": xy, "head_deg": head, "pitch_deg": pitch, "roll_deg": roll,
         "spect_au": spect}
    self._writeline(pre, str(d))
    self._nPixStored += 1

  def storeWavelengths(self, nm):
    """ Store wavelengths for a spectrum
    """
    pre = "w,0"
    d = {"wavelength_nm": nm}
    self._writeline(pre, str(d))

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def finalize(self):
    """ Scan is done, close file etc.
    """
    if self._file:
      print("Closing file `{0}`".format(self._fname))
      self._file.close()
      self._file = None

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _writeline(self, prefix, ln, verbose=True):
    if self._file:
      s = "{0}:{1}".format(prefix, ln)
      self._file.write(s +self._lf)
      if self._toSerial:
        self._toSerial(s +self._lf)
      if verbose:
        print("-> `{0}`".format(s))

# ----------------------------------------------------------------------------
class Scanner(object):
  """Scanner class for taking spectral pictures."""

  SRV_PAN          = const(0)
  SRV_TLT          = const(1)

  PATH_RECT_SPIRAL = const(0)

  def __init__(self, verbose=False):
    """ Acquires all necessary resources.
    """
    self._verbose = verbose
    self._nSrv = 2
    self.toLog("Initializing ...")

    # Create servo manager and servos ...
    self.SM = ServoManager(self._nSrv, verbose=verbose)
    self._Servos = []
    self._SPos = array.array('i', [0] *self._nSrv)
    self._SIDs = array.array('b', [SRV_PAN, SRV_TLT])
    self._Servos.append(Servo(board.SERVO_PAN, verbose=verbose))
    self._Servos[SRV_PAN].change_range(board.PAN_RANGE_US, board.PAN_RANGE_DEG)
    self.SM.add_servo(SRV_PAN, self._Servos[SRV_PAN])
    self._Servos.append(Servo(board.SERVO_TLT, verbose=verbose))
    self._Servos[SRV_TLT].change_range(board.TLT_RANGE_US, board.TLT_RANGE_DEG)
    self.SM.add_servo(SRV_TLT, self._Servos[SRV_TLT])
    self.toLog("Servo manager ready")

    # Create spectrometer instance
    self.SP = C12880MA(trg=board.TRG, st=board.STA, clk=board.CLK, video=board.VID)
    self.SP.begin()
    self.SP.setIntegrationTime_s(0.01)
    time.sleep_ms(200)

    # ...

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def scan(self, fname, size_xy, step_xy_deg, int_s, path=PATH_RECT_SPIRAL):
    """ Performs a scan named `fname` with `path` the scan pattern type,
        `size_xy` the scan dimensions in steps, `step_xy_deg` the step sizes
        in [°], and `int_s` the integration time in [s].
    """
    # Initialize
    done = False
    self._path = path

    try:
      # Create data structure
      self.SI = SpectImg(size_xy, step_xy_deg, int_s, self.SP.channels, fname)
      self.SI.storeWavelengths(self.SP.wavelengths)

      # Set integration time and move to origin
      self.SP.setIntegrationTime_s(max(0.001, int_s))
      self.moveTo()

      # Scan
      for ipix in range(self.SI.nPix):
        # Compute next position and move there
        x,y = self.getNextPos(ipix)
        self.moveTo((x,y), dt_ms=200)

        # Measure spectrum and 3D position and store it
        self.SP.read()
        # ...
        self.SI.storePixel((x,y), 0,0,0, self.SP.spectrum)

    finally:
      self.SI.finalize()

    # Move back to origin
    self.moveTo()
    return done

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def calcPath()

        self._edgelen = 1
        self._nPoints = 0
        self._currXY = [0, 0]


  def getNextPos(self, ipix):
    """ Compute next angular scanner position
    """
    dx = self.SI.stepXY[0]
    dy = self.SI.stepXY[1]
    if self._path == PATH_RECT_SPIRAL:
      if self._nPoints == 0:
        # Origin
        self._currXY = [0, 0]
      else





      #self._edgelen += 1

      self._nPoints += 1
      return self._currXY
    else:
      assert False, "Unknown path"

  def moveTo(self, pos=[0,0], dt_ms=1000):
    """ Move both servos to positon `pos` in [°]
    """
    self.toLog("Moving to  ...")
    self.SM.move(self._SIDs, pos, dt_ms)
    while self.SM.is_moving:
      pass
    self.toLog("... done.")

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def toLog(self, msg):
    """ Print to log if `verbose`==True
    """
    if self._verbose:
      print(msg)

# ----------------------------------------------------------------------------
