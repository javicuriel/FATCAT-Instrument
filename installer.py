import os
import requests
import getpass
import serial
import serial.tools.list_ports
import re
import configparser
import time

config_file = "/etc/systemd/system/instrument.service"

# Create and save init script so application is run as a serivce on application crash or system reboot.
def create_script(uuid, auth_token):
    setup = "[Unit]\nDescription=Carbon measurement system\nAfter=network.target\n\n[Service]\nExecStart=/usr/bin/python -u main.py\nWorkingDirectory=/GAW-Instrument/\nEnvironment=MQTT_UUID=%s\nEnvironment=IBM_TOKEN=%s\nStandardOutput=inherit\nStandardError=inherit\nRestart=always\nRestartSec=2\nKillSignal=SIGINT\n\n[Install]\nWantedBy=sysinit.target"
    file = open(config_file, "w+")
    file.write(setup % (uuid, auth_token))

def lookup_port(name):
    # Looks for and returns port with description
    ports = serial.tools.list_ports.comports()
    for port in ports:
        return port if name in port else None


def set_up_serial(config):
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


def getInstrumentSerialNumber(nano_td_serial):
    # Stop data flow
    nano_td_serial.write("X0000")
    # Empty buffer
    while(len(nano_td_serial.readline())):
        pass
    # Ask for serial number
    nano_td_serial.write("N?")
    # Get serial number
    uuid = None
    # Keep reading until serial number response
    while not uuid:
        serial_number_response = nano_td_serial.readline().rstrip()
        try:
            # Regex for SN
            uuid = re.match('Serial Number=(.*)', serial_number_response).group(1)
        except:
            # Ask for serial number
            nano_td_serial.write("N?")
            uuid = None
    # Start Data flow
    nano_td_serial.write("X1000")
    return uuid


def main():
    if os.path.exists(config_file):
        print("Installation is already complete")
        print("Check: "+config_file)
        return
    if os.getuid() != 0:
        print("Script must be run with sudo!")
        return

    # Getting values from the configuration file
    config = configparser.ConfigParser()
    config.read('config.ini')
    url = eval(config['GENERAL_SETTINGS']['API_URL'])

    print("Welcome to FATCAT-Py Installer")
    print("It appears this is the first time the application is run.")
    print("Would you like to do a Automatic Setup?")
    print("1) Yes")
    print("2) No (Manual UUID & TOKEN set)")
    while(True):
        answer = input("Enter answer: ")
        val = int(answer)
        if(val == 1):
            # Get Serial
            nano_td_serial = set_up_serial(config)
            uuid = getInstrumentSerialNumber(nano_td_serial)
            location = raw_input("Enter location: ")
            lat = raw_input("Enter latitude: ")
            long = raw_input("Enter longitude: ")
            username = raw_input("Enter username for '"+url+"':")
            password = getpass.getpass("Enter password for '"+url+"':")
            data = {'deviceId': uuid, 'location': location, 'lat': lat, 'long': long}
            api = url + 'instruments/add'
            # Get API token for instrument security
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
            print("Invalid answer")

if __name__ == "__main__":
    main()
