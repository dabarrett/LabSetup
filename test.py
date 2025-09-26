import pyvisa
import time

devName = 'ASRL/dev/ttyUSB1::INSTR'
rm = pyvisa.ResourceManager()
print(rm.list_resources('?*'))
load01 = rm.open_resource(devName)

load01.open_timeout = 2500
load01.baud_rate = 9600
load01.write_termination = '\n'
load01.read_termination = '\n'



print(load01)
load01.write('*IDN?')
time.sleep(0.01)
print(load01.read())

#load01.write(":MEASure:VOLTage?")

#while True:
    #print(my_instrument.read_bytes(1))

