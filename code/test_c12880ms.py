from c12880ma import C12880MA

sp = C12880MA(trg=14, st=13, clk=21, video=39)
sp.begin()
sp.read()
print(sp.spectrum)
#print(sp.wavelengths)
