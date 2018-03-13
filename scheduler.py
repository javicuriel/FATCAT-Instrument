from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from Instrument import Instrument
from SerialEmulator import SerialEmulator
from Models import IModule
import serial, os.path, configparser, argparse, logging

config_file = 'config.ini'


def main():
    global instrument
    instrument = get_instrument_config_file()
    # scheduler = set_up_scheduler(instrument)
    instrument._setup_logger('apscheduler')
    # scheduler.start()
    instrument.start()
    # scheduler.shutdown()


def set_up_scheduler(instrument):
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
    }
    scheduler = BackgroundScheduler(jobstores = jobstores)

    events = instrument.get_events()
    for event_name, time in events:
        scheduler.add_job(run_event, 'cron', second=time, id=event_name, replace_existing=True, coalesce= False, max_instances= 100, args = [event_name])

    return scheduler

def run_event(event_name):
    instrument.run_event(event_name)

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
