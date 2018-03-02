import os, pty, serial

# ports = serial.tools.list_ports.comports()
# for p in ports:
#     print(p)

master, slave = pty.openpty()
s_name = os.ttyname(slave)

ser = serial.Serial(s_name)

# To Write to the device
ser.write('Your text')
ser.close()
ser.open()
# print(master)
ser.write('Your text2')
os.fsync()
# To read from the device
print(os.read(master,1000))
