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

PATH_R_SPIRAL    = const(0)
PATH_LR_ZIGZAG   = const(1)
SERVO_MOVE_MS    = const(0)

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
    self.dXY = size_xy # the abs range of x, y e.g.(30,30)-> x:-15,15(deg), y(-15,15)
    self.stepXY = step_xy
    
    # numPix should depend on the stepsizes
    self.nPix = (self.dXY[0]//self.stepXY[0]+1) * (self.dXY[1]//self.stepXY[1]+1)
    self.xyPath = np.zeros((self.nPix, 2))
    
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
    self._verbose = False

    # Check if file exists and recreate it, if needed
    if len(self._fname) > 0:
      try:
        os.stat(self._fname)
        if not self._doOverwr:
          toLog("ERROR: `{0}` already exists and `overwrite=False`", True)
          return
        os.remove(self._fname)
      except OSError:
        pass
      toLog("Opening file `{0}`".format(self._fname), True)
      self._file = open(self._fname, "w")

    # Write header
    d = {"file_version": __file_version__}
    self._writeline("h,0", str(d))
    t = self._rtc.datetime()
    self._date = (t[0], t[1], t[2])
    self._time = (t[4], t[5], t[6])
    d = {"date_yyyymmdd": list(self._date), "time_hhmmss": list(self._time)}
    self._writeline("h,1", str(d))
    d = {"size_xy": list(self.dXY), "step_xy_deg": list(self.stepXY),
         "n_spect": self.nSpect, "t_int_s": self.tInt_s}
    self._writeline("h,2", str(d))
    self._isReady = True

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  @property
  def onToSerial(self, f):
    self._toSerial = f

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def generateScanPath(self, pathType):# =PATH_R_SPIRAL):
    """ Generate a scan path
    """
    self.xyPath[:] = 0
    try:
      if pathType == PATH_R_SPIRAL:
        x = 0;y = 0
        pol = 1;iPix = 1
        maxSteps = 0
        while iPix < self.nPix:
          maxSteps += 1
          for j in range(maxSteps):
            x += self.stepXY[0] *pol
            self.xyPath[iPix] = np.array([x,y])
            iPix += 1
            if iPix > self.nPix -1:
              return
          for j in range(maxSteps):
            y += self.stepXY[1] *pol
            self.xyPath[iPix] = np.array([x,y])
            iPix += 1
            if iPix > self.nPix-1:
              return
          pol = 1 if pol < 0 else -1
      elif pathType == PATH_LR_ZIGZAG:
          range_x,range_y = self.dXY
          max_x = range_x//2 # questionable setting, assumed symmetry here
          max_y = range_y//2
          xs= np.linspace(max_x,-max_x,(range_x//self.stepXY[0]+1)) # pos_x(left) -> neg_x(right)
          ys = np.linspace(max_y,-max_y,(range_y//self.stepXY[1]+1)) # pos_y -> neg_y
          iPix = 0
          for row_idx,y in enumerate(ys):
              for x in xs:
                  if abs(row_idx)%2==1:
                      # odd row: flip the x_scanning direction
                      x = -x
                  self.xyPath[iPix] = np.array([x,y])
                  iPix += 1
      else:
        assert False, "Error: Unknown scan path type"
    finally:
      toLog("Scan path generated.", True)
      print(self.xyPath)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def storePixel(self, xy, head, pitch, roll, spect):
    """ Store a pixel
    """
    pre = "p,{0}".format(self._nPixStored)
    d = {"xy": list(xy), "head_deg": head, "pitch_deg": pitch, "roll_deg": roll,
         "spect_au": list(spect)}
    self._writeline(pre, str(d))
    self._nPixStored += 1

  def storeWavelengths(self, nm):
    """ Store wavelengths for a spectrum
    """
    pre = "w,0"
    d = {"wavelength_nm": list(nm)}
    self._writeline(pre, str(d))

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def finalize(self):
    """ Scan is done, close file etc.
    """
    if self._file:
      toLog("Closing file `{0}`".format(self._fname), True)
      self._file.close()
      self._file = None

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _writeline(self, prefix, ln, verbose=False):
    s = "{0}|{1}".format(prefix, ln)
    if self._file:
      self._file.write(s +self._lf)
    if self._toSerial:
      self._toSerial(s +self._lf)
    if not self._file and not self._toSerial:
      print(s)
    else:
      toLog("`{0}`".format(s), verbose)

# ----------------------------------------------------------------------------
class Scanner(object):
  """Scanner class for taking spectral pictures."""

  SRV_PAN          = const(0)
  SRV_TLT          = const(1)

  def __init__(self, verbose=False):
    """ Acquires all necessary resources.
    """
    self._verbose = verbose
    self._nSrv = 2
    toLog("Initializing ...", True)

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
    toLog("Servo manager ready", True)

    # Create spectrometer instance
    self.SP = C12880MA(trg=board.TRG, st=board.STA, clk=board.CLK, video=board.VID)
    self.SP.begin()
    self.SP.setIntegrationTime_s(0.01)
    time.sleep_ms(200)
    toLog("Spectrometer ready", True)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def setupScan(self, fname, size_xy, step_xy_deg, int_s, path):
    """ Sets up a scan named `fname` with `path` the scan pattern type,
        `size_xy` the scan dimensions in steps, `step_xy_deg` the step sizes
        in [°], and `int_s` the integration time in [s]. If `fname` is empty,
        the output is send to the REPL.
    """
    print(PATH_R_SPIRAL) # debugging
    # Create data structure
    self.SI = SpectImg(size_xy, step_xy_deg, int_s, self.SP.channels, fname)
    self.SI.storeWavelengths(self.SP.wavelengths)

    # Set integration time and move to origin
    self.SP.setIntegrationTime_s(max(0.001, int_s))
    self.moveTo() # init for [0,0] in angle, (1470, 1474) in us

    # Calculate scan path
    self.SI.generateScanPath(path)

    # Ready to scan
    self._iPix = 0


  def scanNext(self):
    """ Scans the next point, if any
    """
    if self._iPix < self.SI.nPix:
      # Compute next position and move there
      x,y = self.SI.xyPath[self._iPix]
      self.moveTo((x,y), dt_ms=SERVO_MOVE_MS)

      # Measure spectrum and 3D position and store it
      self.SP.read()
      self.SI.storePixel((x,y), 0,0,0, self.SP.spectrum)

      self._iPix += 1
      return True
    else:
      # Close file, if needed and move back to origin
      self.SI.finalize()
      self.moveTo()
      return False

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def moveTo(self, pos=[0,0], dt_ms=1000):
    """ Move both servos to positon `pos` in [°]
    """
    toLog("Moving to  ...", self._verbose)
    self.SM.move(self._SIDs, pos,dt_ms)
    # print(pos,dt_ms)
    while self.SM.is_moving:
      pass
    toLog("... done.", self._verbose)

# ----------------------------------------------------------------------------
def toLog(msg, verbose=False):
  """ Print to log if `verbose` == True
  """
  if verbose:
    print("c,_|" +msg)

# ----------------------------------------------------------------------------
