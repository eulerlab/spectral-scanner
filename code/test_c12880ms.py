import time
import board
from driver.c12880ma import C12880MA

sp = C12880MA(trg=board.TRG, st=board.STA, clk=board.CLK, video=board.VID)
sp.begin()
sp.setIntegrationTime_s(0.01)
time.sleep_ms(200)

sp.read()
print(sp.wavelengths)
print(sp.spectrum)
