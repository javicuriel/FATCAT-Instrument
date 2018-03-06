import os, pty, time, psutil
from Instrument import *
from SerialEmulator import *
import datetime

def main():

    instrument = Instrument(
        mqtt_host = MQTT_SERVER,
        mqtt_port = MQTT_PORT,
        mqtt_keep_alive = MQTT_KEEPALIVE,
        mqtt_qos = MQTT_QOS,
        mqtt_lost_messages_retry_time = MQTT_SEND_LOST_TIME,

        serial_port_description = SERIAL_PORT_DESCRIPTION,
        serial_baudrate = SERIAL_BAUDRATE,
        serial_parity = SERIAL_PARITY,
        serial_stopbits = SERIAL_STOPBITS,
        serial_bytesize = SERIAL_BYTESIZE,
        serial_timeout = SERIAL_TIMEOUT

    )
    ser = SerialEmulator()
    instrument._serial = ser

    pump = IModule(name = 'pump')

    pump.set_action('on', 'U1000')
    pump.set_action('off', 'U0000')

    pump = IModule(name = 'pump').set_actions({'on':'U1000','off':'U1000'})
    # instrument.add_module(pump)
    # instrument.add_module(reader)
    instrument.add_module(IModule(name = 'pump').set_actions({'on':'U1000','off':'U1000'}))
    instrument.add_module(IModule(name = 'res').set_actions({'on':'U1000','off':'U1000'}))


    instrument.start()


    # pump.run_action('os')
    # instrument.stop()
    # DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    # t = 'jsj'
    #
    # LOG_FORMAT = '%(asctime)s [%(levelname)s] %(instrument_uuid)s - %(module_name)s :: %(message)s '
    # # get_log_info
    # logging.basicConfig(format=LOG_FORMAT,datefmt=DATE_FORMAT, filename='instrument_main.log', level=logging.DEBUG)
    # extra = {'instrument_uuid': '546435764', 'module_name': 'pump', 'dsdas' :'ksdkds'}
    # logger = logging.getLogger('instrument')
    # logger = logging.LoggerAdapter(logger, extra)
    # logger.warning('me')
    # extra['module_name'] = 'new_pump'
    # logger.warning('sd')


main()
