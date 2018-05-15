import os
import requests
import getpass


# config_file = "/etc/systemd/system/instrument.service"
config_file = "./instrument.service"

def create_script(uuid, auth_token):
    setup = "[Unit]\nDescription=Carbon measurement system\nAfter=network.target\n\n[Service]\nExecStart=/usr/bin/python3 -u main.py\nWorkingDirectory=/GAW-Instrument/\nEnvironment=MQTT_UUID=%s\nEnvironment=IBM_TOKEN=%s\nStandardOutput=inherit\nStandardError=inherit\nRestart=always\nRestartSec=2\n\n[Install]\nWantedBy=sysinit.target"
    file = open(config_file, "w+")
    file.write(setup % ("'"+uuid+"'", "'"+auth_token+"'"))

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
    print("2) No (Manual UUID set)")
    while(True):
        answer = input("Enter answer: ")
        try:
            val = int(answer)
            if(val == 1):
                # TODO
                # Stop serial data flow and ask for id
                uuid = "super_cool_id_nuevo_siii"
                location = raw_input("Enter location: ")
                lat = raw_input("Enter latitude: ")
                long = raw_input("Enter longitude: ")
                username = raw_input("Enter username for CarbonMeasurmentApplication: ")
                password = getpass.getpass('Enter password:')
                data = {'deviceId': uuid, 'location': location, 'lat': lat, 'long': long}
                api = 'https://carbonmeasurmentsystem.eu-gb.mybluemix.net/instruments/add'
                response = requests.post(api, data=data, auth=(username,password))
                if(response.status_code == 200):
                    create_script(uuid, response.text)
                    os.system("sudo pip install -r requirements.txt")
                    print("Instrument setup was successfull!")
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
