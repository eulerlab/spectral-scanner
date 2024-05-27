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
import machine
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
    self._stepLists     = []                              # only for parabolic
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
    print('target pos {}'.format(pos))
    # print(servos) # JD debugging
    if self._isMoving:
      # Stop ongoing move
      self._Timer.init(period=-1)
      self._isMoving = False

    # Prepare new move
    # do we still need nSteps???
    nSteps = dt_ms /RATE_MS # RATE_MS=20
    # print('nSteps_{}=dt_ms_{}/RATE_MS_{}'.format(nSteps,dt_ms,RATE_MS))
    
    # by default ???? linear or parabolic?
    if nSteps > _STEP_ARRAY_MAX: # 500
      # Too many steps for a paraboloid trajectory
      print("nSteps more than 500, use linear moving pattern")
      lin_vel = True
      print("WARNING: {0} is too many steps; going linear".format(int(nSteps)))
    
    for idxS, SID in enumerate(servos):
      # idxS == SID due to:
      # SRV_PAN = const(0)
      # SRV_TLT = const(1)
      
      if not self._Servos[SID]:
        continue
      
      ## carry on the value from Scanner class to SM class
      self._SIDList[idxS] = SID
      
      # set the target position for respective servos
      self._targetPosList[idxS] = self._Servos[SID].angle_in_us(pos[idxS])
      
      if nSteps > 0:
        # A time period is given, therefore calculate the step sizes for this
        # servo's move, with ...
                                                                                         
        p = self._servoPos[SID] # acquire the initial positions
        
        dp = self._targetPosList[idxS] -p # calculate the displacement
        # print('servo{},initial_pos(us):{}, target_pos(us):{},total displacement(us):{}'.format(
        #    idxS,p,self._targetPosList[idxS],dp))
        if lin_vel:
          # ... linear velocity
          s = round(dp/RATE_MS)  # why do we need this?
          self._currPosList[idxS] = p +s # the next state
          self._stepSizeList[idxS] = s # delta_displacement per step == stepsize
          # print('linear velocity(us/step)={},nextPos={},_servoPos={}'.
          #      format(s,self._currPosList[idxS],self._servoPos[idxS]))
        else:
          # ... paraboloid trajectory
          print('parabolic trajectory')
          p_n = nSteps -1
          p_n2 = p_n /2
          p_peak = p_n2**2
          p_func = [-(j +1 -p_n2)**2 +p_peak for j in range(int(nSteps))]
          p_scal = dp /sum(p_func)
          for iv in range(p_n -1):
            self._stepLists[idxS][iv] = int(p_func[iv] *p_scal)
          self._stepSizeList[idxS] = 0
      else:
        ## if nStep==0
        ## Move directly, therefore update already the final position
        self._servoPos[SID] = self._targetPosList[idxS]
          
    self._nToMove = len(self._Servos)# n #
    self._dt_ms = dt_ms
    self._nSteps = int(nSteps) -1 # why -1????
    
    ## done setting up
    ## start moving
    if dt_ms == 0:
      ## equivalent to nSteps =0 
      # move the servo directly to the targetPositions
      for idxS in range(len(self._Servos)):
        target_p = int(self._targetPosList[idxS])
        
        ## the code that actually does the move
        self._Servos[self._SIDList[idxS]].write_us(target_p) 
    else:
      # Setup timer to keep moving them in the requested time
      ## trigger _cb() every 20ms
      self._Timer.init(mode=Timer.PERIODIC, period=RATE_MS, callback=self._cb)
      self._isMoving = True

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  def _cb(self, value):
    if self._isMoving:
      # Update every servo in the list
      for idxS in range(self._nToMove):
        SID = self._SIDList[idxS]
        for step in range(self._nSteps+1):
            p = int(self._currPosList[idxS])
            # print('debug,step_{},p_{}'.format(step,p))
            if p >= self._targetPosList[idxS]:
                # the next pos is beyond target
                target_p = int(self._targetPosList[idxS])
                
                # set the servo to target position
                self._servoPos[SID] = target_p
                self._Servos[SID].write_us(target_p)
                self._isMoving = False
                # print('stopped at {}/{} step'.format(step+1,self._nSteps+1))
                break
            else:
              self._Servos[SID].write_us(p)
              if self._stepSizeList[idxS] == 0:
                ## WHY ==0 ?-> paraboloid????
                # Paraboloid trajectory
                # print('self._stepSizeList[idxS]==0, paraboloid!!!!')
                self._currPosList[idxS] += self._stepLists[idxS][self._nSteps]
              else:
                # Linear trajectory
                # set the next position
                self._currPosList[idxS] += self._stepSizeList[idxS]
                # if step%10 ==0:
                    #print("linear, iter: {}/50 step, at {}, next {} ".format(
                    #    step,p,self._currPosList[idxS]))
  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  @property
  def is_moving(self):
    """ Returns True if a move is still ongoing
    """
    return self._isMoving

# ----------------------------------------------------------------------------
