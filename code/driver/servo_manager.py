# ----------------------------------------------------------------------------
# servo_manager.py
# Class to manage and control a number of servos
#
# The MIT License (MIT)
# Copyright (c) 2020 Thomas Euler
# 2020-01-03, v1
# 2020-08-02, v1.1 ulab
# ----------------------------------------------------------------------------
import time
from machine import Timer
import ulab as np
from micropython import alloc_emergency_exception_buf
alloc_emergency_exception_buf(100)

__version__       = "0.1.1.0"
RATE_MS           = const(20)
_STEP_ARRAY_MAX   = const(500)

# ----------------------------------------------------------------------------
class ServoManager(object):
  """Class to manage and control a number of servos"""

  TYPE_NONE       = const(0)
  TYPE_HORIZONTAL = const(1)
  TYPE_VERTICAL   = const(2)
  TYPE_SENSOR     = const(3)

  def __init__(self, n, max_steps=_STEP_ARRAY_MAX, verbose=False):
    """ Initialises the management structures
    """
    self._isVerbose     = verbose
    self._isMoving      = False
    self._nChan         = max(1, n)
    self._Servos        = [None]*n                        # Servo objects
    self._servo_type    = np.array([0]*n, dtype=np.uint8) # Servo type
    self._servo_number  = np.array([-1]*n, dtype=np.int8) # Servo number
    self._servoPos      = np.array([0]*n)                 # Servo pos [us]
    self._SIDList       = np.array([-1]*n, dtype=np.int8) # Servos to move next
    self._targetPosList = np.array([0]*n)                 # Target pos [us]
    self._currPosList   = np.array([-1]*n)                # Current pos [us]
    self._stepSizeList  = np.array([0]*n)                 # .. step sizes [us]
    self._stepLists     = []
    for i in range(n):
      self._stepLists.append(np.array([0]*max_steps))
    self._nToMove       = 0                               # # of servos to move
    self._dt_ms         = 0                               # Time period [ms]
    self._nSteps        = 0                               # # of steps to move
    self._Timer         = Timer(0)
    self._Timer.init(period=-1)

  def add_servo(self, i, servoObj, pos=0):
    """ Add at the entry `i` of the servo list the servo object, which has to
        define the following functions:
        - `write_us(t_us)`
        - `angle_in_us(value=None)`
        - `off()`
        - `deinit()`
    """
    if i in range(self._nChan):
      self._Servos[i] = servoObj
      self._servoPos[i] = servoObj.angle_in_us()
      self._servo_number[i] = i
      if self._isVerbose:
        print("Add servo #{0:-2.0f}, at {1} us"
              .format(i, int(self._servoPos[i])))

  def set_servo_type(self, i, type):
    """ Change servo type (see `TYPE_xxx`)
    """
    if i in range(self._nChan) and self._Servos[i] is not None:
      self._servo_type[i] = type

  def turn_all_off(self, deinit=False):
    """ Turn all servos off
    """
    for servo in self._Servos:
      if not servo is None:
        servo.off()
        if deinit:
          servo.deinit()

  def deinit(self):
    """ Clean up
    """
    self._Timer.deinit()
    self.turn_all_off(deinit=True)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  '''
  @timed_function
  def move_timed(self, servos, pos, dt_ms=0, lin_vel=True):
    self.move(servos, pos, dt_ms)
  '''
  @micropython.native
  def move(self, servos, pos, dt_ms=0, lin_vel=True):
    """ Move the servos in the list to the positions given in `pos`.
        If `dt_ms` > 0, then it will be attempted that all servos reach the
        position at the same time (that is after `dt_ms` ms)
    """
    if self._isMoving:
      # Stop ongoing move
      # ...
      self._Timer.init(period=-1)
      self._isMoving = False

    # Prepare new move
    n = 0
    nSteps = dt_ms /RATE_MS
    if nSteps > _STEP_ARRAY_MAX:
      # Too many steps for a paraboloid trajectory
      lin_vel = True
      print("WARNING: {0} is too many steps; going linear".format(int(nSteps)))

    for iS, SID in enumerate(servos):
      if not self._Servos[SID]:
        continue
      self._SIDList[n] = SID
      self._targetPosList[n] = self._Servos[SID].angle_in_us(pos[iS])
      if nSteps > 0:
        # A time period is given, therefore calculate the step sizes for this
        # servo's move, with ...
        p = self._servoPos[SID]
        dp = self._targetPosList[n] -p
        #print("dp=", dp)
        if lin_vel:
          # ... linear velocity
          s = int(dp /nSteps)
          self._currPosList[n] = p +s
          self._stepSizeList[n] = s
        else:
          # ... paraboloid trajectory
          p_n = nSteps -1
          p_n2 = p_n /2
          p_peak = p_n2**2
          p_func = [-(j +1 -p_n2)**2 +p_peak for j in range(int(nSteps))]
          p_scal = dp /sum(p_func)
          for iv in range(p_n -1):
            self._stepLists[n][iv] = int(p_func[iv] *p_scal)
          self._stepSizeList[n] = 0
          #print(dp, nSteps, p_n, p_scal, sum(self._stepLists[iS]))
          #print(self._stepLists[iS])
      else:
        # Move directly, therefore update already the final position
        self._servoPos[SID] = self._targetPosList[iS]
      n += 1
    self._nToMove = n
    self._dt_ms = dt_ms
    self._nSteps = int(nSteps) -1

    # Initiate move
    if dt_ms == 0:
      # Just move them w/o considering timing
      for iS in range(n):
        p = int(self._targetPosList[iS])
        self._Servos[self._SIDList[iS]].write_us(p)
    else:
      # Setup timer to keep moving them in the requested time
      self._Timer.init(mode=Timer.PERIODIC, period=RATE_MS, callback=self._cb)
      self._isMoving = True

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _cb(self, value):
    if self._isMoving:
      # Update every servo in the list
      for iS in range(self._nToMove):
        SID = self._SIDList[iS]
        if self._nSteps > 0:
          # Move is ongoing, update servo position ...
          p = int(self._currPosList[iS])
          self._Servos[SID].write_us(p)
          if self._stepSizeList[iS] == 0:
            # Paraboloid trajectory
            self._currPosList[iS] += self._stepLists[iS][self._nSteps]
            #print("para", self._nSteps, p, self._stepLists[iS][self._nSteps])
          else:
            # Linear trajectory
            self._currPosList[iS] += self._stepSizeList[iS]
            #print("lin ", self._nSteps, p, self._stepSizeList[iS])
        else:
          # Move has ended, therefore set servo to the target position
          tp = int(self._targetPosList[iS])
          self._servoPos[SID] = tp
          self._Servos[SID].write_us(tp)
      if self._nSteps > 0:
        self._nSteps -= 1
        #print("curr", self._currPosList)
      else:
        # Move is done
        self._isMoving = False
        #print("targ", self._targetPosList)

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  @property
  def is_moving(self):
    """ Returns True if a move is still ongoing
    """
    return self._isMoving

# ----------------------------------------------------------------------------
