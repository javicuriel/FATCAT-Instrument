import os
import requests
import getpass
import serial
import serial.tools.list_ports
import re
import configparser
import time


config_file = "/etc/systemd/system/instrument.service"
url = "https://carbonmeasurmentsystem.eu-gb.mybluemix.net/"

def create_script(uuid, auth_token):
    setup = "[Unit]\nDescription=Carbon measurement system\nAfter=network.target\n\n[Service]\nExecStart=/usr/bin/python -u main.py\nWorkingDirectory=/GAW-Instrument/\nEnvironment=MQTT_UUID=%s\nEnvironment=IBM_TOKEN=%s\nStandardOutput=inherit\nStandardError=inherit\nRestart=always\nRestartSec=2\n\n[Install]\nWantedBy=sysinit.target"
    file = open(config_file, "w+")
    file.write(setup % (uuid, auth_token))

def lookup_port(name):
    # Looks for and returns port with description
    ports = serial.tools.list_ports.comports()
    for port in ports:
        return port if name in port else None


def set_up_serial():
    config = configparser.ConfigParser()
    config.read('config.ini')
    serial_port_description = eval(config['SERIAL_SETTINGS']['SERIAL_PORT_DESCRIPTION'])
    # Waits 2 seconds before trying again if no port found
    # and doubles time each try with maximum 32 second waiting time
    port = lookup_port(serial_port_description)
    wait = 2
    while not port:
        print("No TCA found, waiting " + str(wait) + " seconds...")
        time.sleep(wait)
        if wait < 32:
            wait = wait*2
        port = lookup_port(serial_port_description)

    print("Serial port found: " + port.device)

    return serial.Serial(
        port = port.device,
        baudrate = eval(config['SERIAL_SETTINGS']['SERIAL_BAUDRATE']),
        parity = eval(config['SERIAL_SETTINGS']['SERIAL_PARITY']),
        stopbits = eval(config['SERIAL_SETTINGS']['SERIAL_STOPBITS']),
        bytesize = eval(config['SERIAL_SETTINGS']['SERIAL_BYTESIZE']),
        timeout = eval(config['SERIAL_SETTINGS']['SERIAL_TIMEOUT'])
    )

def main():
    if os.path.exists(config_file):
        print("Installation is already complete")
        print("Check: "+config_file)
        return
    if os.getuid() != 0:
        print("Script must be run with sudo!")
        return

    print("Welcome to FATCAT-Py Installer")
    print("It appears this is the first time the application is run.")
    print("Would you like to do a Automatic Setup?")
    print("1) Yes")
    print("2) No (Manual UUID & TOKEN set)")
    while(True):
        answer = input("Enter answer: ")
        try:
            val = int(answer)
            if(val == 1):
                # Get Serial
                nano_td_serial = set_up_serial()
                # Stop data flow
                nano_td_serial.write("X0000")
                while(len(nano_td_serial.readline())):
                    pass
                # Ask for serial number
                nano_td_serial.write("N?")
                # Get serial number
                serial_number_response = nano_td_serial.readline().rstrip()
                nano_td_serial.write("X1000")
                # Regex for SN
                uuid = re.match('Serial Number=(.*)', serial_number_response).group(1)
                location = raw_input("Enter location: ")
                lat = raw_input("Enter latitude: ")
                long = raw_input("Enter longitude: ")
                username = raw_input("Enter username for '"+url+"':")
                password = getpass.getpass("Enter password for '"+url+"':")
                data = {'deviceId': uuid, 'location': location, 'lat': lat, 'long': long}
                api = url + 'instruments/add'
                response = requests.post(api, data=data, auth=(username,password))
                if(response.status_code == 200):
                    create_script(uuid, response.text)
                    os.system("sudo pip install -r requirements.txt")
                    os.system("sudo systemctl enable instrument.service")
                    os.system("sudo systemctl start instrument.service")

                    print("Instrument setup was successfull!")
                    print("If requirements installation failed, use 'sudo pip install -r requirements.txt'")
                else:
                    print("Error occurred")
                    print(response.text)
                return
            elif(val == 2):
                uuid = raw_input("Enter UUID: ")
                auth_token = raw_input("Enter Token: ")
                create_script(uuid, response.text)
                os.system("pip install -r requirements.txt")
                return
            else:
                raise ValueError
        except ValueError:
            print("Invalid answer")

main()
