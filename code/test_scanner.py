from scanner import Scanner, SpectImg

sc = Scanner(verbose=False)
sc.setupScan("", (5,5), (10,10), 0.1)
'''
while sc.scanNext():
  pass
'''
