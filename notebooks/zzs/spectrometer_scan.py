
# coding: utf-8

# In[30]:


import time
import scripts.ar2py as arduino

# import seabreeze (use 'pyseabreeze')
import seabreeze.spectrometers as sb
#
import os
import math
import numpy as np
import matplotlib.pyplot as plt

import h5py

# set graphics to be plotted in the notebook
get_ipython().run_line_magic('matplotlib', 'inline')


# In[31]:


#arduino
# Set connection parameters
#
comPortName   = "COM3"
comPortBaud   = 57600

# Create an Arduino object and open a link to the board
#
ard = arduino.Arduino()
ard.openLink(comPortName, comPortBaud)
# Request version of firmware and size of available memory
#
result = ard.sendCommand("VER")


# In[32]:


#arduino test
# Define pins 2 and 3 as servo pins (mode=3) and move both
# servos to the center
#
result = ard.sendCommand("SDM P=2,3 M=3,3")     
result = ard.sendCommand("SDV P=2,3 V=40,40")


# In[33]:


#sepctrometer
#
spec = sb.Spectrometer.from_serial_number("USB2+F02461")
# serial number
print (spec.serial_number)
# model
print (spec.model)
# number of pixels (as returned by seabreeze)
print (spec.pixels)
# set the integration time in microseconds
micro_time=200000
spec.integration_time_micros(micro_time)


# In[23]:


#micro_time=200000
#spec.integration_time_micros(micro_time)


# In[35]:


#spectrometer test
# return an array containing all wavelengths
wavelengths=spec.wavelengths()
# return the newest aquired spectrum (with dark count and nonlinearity correction)
intensities=spec.intensities(correct_dark_counts=True, correct_nonlinearity=True)
plt.plot(wavelengths,intensities)
plt.xlabel ("Wavelenght (nm)")
plt.ylabel("Counts (raw output of spectrometer)")


# In[36]:


#arduino and spectrometer
# Switch feedback to history off
#
ard.setVerbose(False)

# Move to a series of positions and wait at each position for
# half a second
#
minvalue=10
maxvalue=50
stepvalue=1
numvalue=int((maxvalue-minvalue)/stepvalue)
arrayvalue=np.zeros((numvalue,numvalue,spec.pixels),np.float64)
x_count=0
for x in range(minvalue, maxvalue, stepvalue):
    y_count=0
    for y in range(minvalue, maxvalue, stepvalue):
        result = ard.sendCommand("SDV P=2,3 V={0},{1}".format(x, y))
        #time.sleep(0.2)
        # return an array containing all wavelengths
        wavelengths=spec.wavelengths()
        # return the newest aquired spectrum (with dark count and nonlinearity correction)
        intensities=spec.intensities(correct_dark_counts=True, correct_nonlinearity=True)
        arrayvalue[x_count,y_count,:]=intensities
        time.sleep(micro_time/1000000+0.1)
        y_count=y_count+1
    x_count=x_count+1
        

          


# In[37]:


#save data
#h5f = h5py.File('spectral_results.h5', 'w')
current_time=time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
h5f = h5py.File('spectral_results.h5', 'a')
h5f.create_dataset(current_time, data=arrayvalue)
h5f.close()    

# Go back to center
#
result = ard.sendCommand("SDV P=2,3 M=90,90")     

# Switch feedback to history back on
#
ard.setVerbose(True)  


# In[38]:


#arduino
# Clear pin definitions and close the serial connection
#
result = ard.sendCommand("CLR")     
ard.closeLink()


# In[39]:


#h5f.close()
arrayvalue.shape

