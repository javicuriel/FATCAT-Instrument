from Instrument import Instrument
from SerialEmulator import SerialEmulator
from Models import IModule
import serial, os.path, configparser, argparse, logging, time

config_file = 'config.ini'
MINUTE = 60

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Sets intrument to DEBUG mode",action="store_true")
    args = parser.parse_args()
    # If there is config file, create instrument with config file settings
    if os.path.exists(config_file):
        global instrument
        instrument = get_instrument_config_file()
        instrument.set_mode('analisis', ['licor:on', 'extp:off', 'valve:on', 'pump:on'])
        instrument.set_mode('sampling', ['pump:off', 'valve:off', 'extp:on', 'licor:off'])

        if args.debug:
            logging.getLogger(instrument.name).setLevel(logging.DEBUG)
            logging.getLogger(instrument.scheduler.name).setLevel(logging.DEBUG)

        # instrument.scheduler.add_job(otro_analisis, 'interval', seconds= 10 , name = 'RunAnalysis', id = 'RunAnalysis', replace_existing=True, coalesce= True)
        instrument.scheduler.add_job(run_analysis, 'interval', seconds= 10 , name = 'RunAnalysis', id = 'RunAnalysis', replace_existing=True)

        instrument.start()

def otro_analisis():
    print("Otro analisis cada 6 segundos")


def run_analysis():
    # ANALYSIS_MODE
    instrument.run_mode('analisis')
    # OVEN
    # time.sleep(5)
    instrument.run_action('oven', 'on')
    # time.sleep(27*MINUTE)
    instrument.run_action('oven', 'on')
    # SAMPLING_MODE
    instrument.run_mode('sampling')



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
        serial_timeout = eval(config['SERIAL_SETTINGS']['SERIAL_TIMEOUT']),
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
