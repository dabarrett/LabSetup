import sys, ftd2xx as ftd
d = ftd.open(0)    # Open first FTDI device
print(d.getDeviceInfo())