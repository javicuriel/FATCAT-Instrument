from Instrument import Instrument
from SerialEmulator import SerialEmulator
from models import IModule
from apscheduler.triggers.cron import CronTrigger
import serial, os.path, configparser, argparse, logging, time
import helpers

config_file = 'config.ini'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Sets intrument to DEBUG mode",action="store_true")
    parser.add_argument("--dev", help="Sets Serial Emulator",action="store_true")
    args = parser.parse_args()

    # If there is config file, create instrument with config file settings
    if os.path.exists(config_file):
        global instrument
        instrument = get_instrument_config_file(args.dev)

        if args.debug:
            logging.getLogger(instrument.name).setLevel(logging.DEBUG)
            logging.getLogger(instrument.scheduler.name).setLevel(logging.DEBUG)

        # instrument.run_action('pump', 'flow=10')
        # instrument.get_jobs()
        instrument.start()


# Sets up instrument with config file settings
def get_instrument_config_file(development):
    config = configparser.ConfigParser()
    config.read(config_file)
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
        # Test serial emulator
        serial_emulator = development
    )
    if(development):
        ser = SerialEmulator()
        instrument._serial = ser
    set_options_config_file(config, instrument)
    return instrument

# Sets up instrument's modules with config file settings
def set_options_config_file(config, instrument):
    for name in config['MODULES']:
        module = IModule(name = name)
        for action in eval(config['MODULES'][name]):
            a, sa = action.split(':')
            module.set_action(a, sa)
        instrument.add_module(module)

    for mode in config['MODES']:
        array_actions = helpers.get_array_actions(eval(config['MODES'][mode]))
        instrument.add_mode(mode, array_actions)

    jobs = [section for section in config.sections() if section.startswith('JOB.')]
    for job in jobs:
        targs = helpers.getTriggerArgs(eval(config.get(job,'trigger')))
        array_actions = helpers.get_array_actions(eval(config[job]['actions']))
        # Name is job[4:] because removing 'JOB.'
        instrument.add_job(name = job[4:], actions = array_actions, **targs)



if __name__ == "__main__":
    main()
