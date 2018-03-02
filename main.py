import os, pty, time
from Instrument import *

def main():
    pump = IModule(name = 'pump')

    pump.set_action('on', 'U1000')
    pump.set_action('off', 'U0000')

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
    ser, master = helper_create_serial()
    instrument._serial = ser
    instrument.add_module(pump)
    instrument.start()
    pump.run_action('os')
    instrument.stop()
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

def helper_create_serial():
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    ser = serial.Serial(s_name)
    return ser, master

main()
