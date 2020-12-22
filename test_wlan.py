import driver.wlan as wlan
import network
from scanner import SpectImg, Scanner

'''
wlan.connect()
wlan.syncDateTime()
'''

fname = "temp.sim"

try:
  '''
  si = SpectImg((20,20), (1,1), 0.001, 288, fname)
  si.storePixel((0,0), 360,0,12, [i for i in range(288)])
  '''

  sc = Scanner()
  #sc.scan(fname, (3,3), (5,5), 0.001)

  sc.moveTo(pos=[0,0])

  sc.moveTo(pos=[-45,-45])
  sc.moveTo(pos=[ 45, 45])

  sc.moveTo(pos=[0,0])

finally:
  '''
  si.finalize()
  '''
  pass

"""
f = open("temp.sim", "r")
for i in range(10):
  print(f.readline()[:-2])
"""
