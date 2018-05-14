import os.path
import os
import requests
import getpass

def set_enviroment_variables(uuid, auth_token):
    os.system("echo '\n# For MQTT Client Autentication' >>~/.bash_profile")
    os.system("echo export MQTT_UUID=\\'"+uuid+"\\' >>~/.bash_profile")
    os.system("echo export IBM_TOKEN=\\'"+auth_token+"\\' >>~/.bash_profile")

if not (os.environ.get("MQTT_UUID") and os.environ.get("IBM_TOKEN")):
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
                api = 'http://localhost:3000/instruments/add'
                response = requests.post(api, data=data, auth=(username,password))
                if(response.status_code == 200):
                    set_enviroment_variables(uuid, response.text)
                    print("Instrument setup was successfull!")
                else:
                    print(response.text)
                break
            elif(val == 2):
                uuid = raw_input("Enter UUID: ")
                auth_token = raw_input("Enter Token: ")
                set_enviroment_variables(uuid, auth_token)
                break
                # os.environ["MQTT_UUID"] = "'"+uuid+"'"
                # os.environ["T_IBM_TOKEN"] = "'"+auth_token+"'"
                # print os.environ["MQTT_UUID"]
                # print os.environ["T_IBM_TOKEN"]
            else:
                raise ValueError
        except ValueError:
            print("Invalid answer")
