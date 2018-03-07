from Instrument import *
from SerialEmulator import *
import os.path, configparser

config_file = 'config.ini'

def main():
    # If there is config file, create instrument with config file settings
    if os.path.exists(config_file):
        instrument = get_instrument_config_file()
        instrument.start()



# Sets up instrument with config file settings
def get_instrument_config_file():
    config = configparser.ConfigParser()
    config.read(config_file)
    ser = SerialEmulator()
    instrument = Instrument(
        mqtt_host = eval(config['MQTT_SETTINGS']['MQTT_SERVER']),
        mqtt_port = eval(config['MQTT_SETTINGS']['MQTT_PORT']),
        mqtt_keep_alive = eval(config['MQTT_SETTINGS']['MQTT_KEEPALIVE']),
        mqtt_qos = eval(config['MQTT_SETTINGS']['MQTT_QOS']),

        serial_port_description = eval(config['SERIAL_SETTINGS']['SERIAL_PORT_DESCRIPTION']),
        serial_baudrate = eval(config['SERIAL_SETTINGS']['SERIAL_BAUDRATE']),
        serial_parity = eval(config['SERIAL_SETTINGS']['SERIAL_PARITY']),
        serial_stopbits = eval(config['SERIAL_SETTINGS']['SERIAL_STOPBITS']),
        serial_bytesize = eval(config['SERIAL_SETTINGS']['SERIAL_BYTESIZE']),
        serial_timeout = eval(config['SERIAL_SETTINGS']['SERIAL_TIMEOUT'])
    )
    instrument._serial = ser
    set_modules_config_file(config, instrument)
    return instrument

# Sets up instrument's modules with config file settings
def set_modules_config_file(config, instrument):
    for key in config['MODULES']:
        module = IModule(name = key)
        for action in eval(config['MODULES'][key]):
            a, sa = action.split(':')
            module.set_action(a, sa)
        instrument.add_module(module)

main()
