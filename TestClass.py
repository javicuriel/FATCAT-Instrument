import unittest
from Instrument import *
import os, pty
import paho.mqtt.publish as publish
from SerialEmulator import *
import time

logging.basicConfig(filename='instrument_tests.log', level=logging.INFO)

def helper_publish(topic, message):
    publish.single(
        topic,
        payload=message,
        qos=0,
        retain=False,
        hostname="localhost",
        port=1883,
        client_id="",
        keepalive=60,
        will=None,
        auth=None,
        tls=None,
        protocol=mqtt.MQTTv311,
        transport="tcp"
    )

def helper_create_serial():
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    ser = serial.Serial(s_name)
    return ser, master

def helper_serial_action(value):
    return str(value + 10)

class InstrumentTest(unittest.TestCase):
    def setUp(self):

        # Instrument creation
        self.instrument = Instrument(
            mqtt_host = MQTT_SERVER,
            mqtt_port = MQTT_PORT,
            mqtt_keep_alive = MQTT_KEEPALIVE,
            mqtt_qos = MQTT_QOS,
            mqtt_lost_messages_retry_time = MQTT_SEND_LOST_TIME,
        )

        self.serial = SerialEmulator()
        self.instrument._serial = self.serial

    def testModuleReading(self):
        self.assertTrue(False, 'message')


    def testModuleOperationStaticAction(self):
        test_module = IModule(name = 'test_module')
        self.instrument.add_module(test_module)
        self.instrument.start()

        topic = self.instrument.uuid + '/modules/'+ test_module.name

        tests = 10

        for i in range(tests):
            # Action sent by MQTT
            action = str(i)
            # Serial Action that should be executed with MQTT action
            serial_action = 'serial_action_' + str(i)
            # Add operable action to module
            test_module.set_action(action, serial_action)
            # Publish MQTT message with the action
            helper_publish(topic, action)
            # Get Serial log
            time.sleep(.005)
            serial_log = self.serial._receivedData
            # Assert that an action sent by MQTT executed the right serial action
            self.assertEqual(serial_log, serial_action)
            self.serial._receivedData = ""

        self.instrument.stop()

    def testModuleOperationDynamicAction(self):
        test_module = IModule(name = 'test_module')
        self.instrument.add_module(test_module)
        self.instrument.start()

        topic = self.instrument.uuid + '/modules/'+ test_module.name

        tests = 10

        for i in range(tests):
            # Action sent by MQTT
            action_name = 'value'
            # Add operable action to module (Custom user function)
            test_module.set_action(action_name, helper_serial_action)
            # Publish MQTT message with the action
            # Format {id}/modules/{action_name}={value}
            helper_publish(topic, action_name + '=' + str(i))
            # Get Serial log
            time.sleep(.005)
            serial_log = self.serial._receivedData
            # Assert that an action sent by MQTT executed the right serial action
            self.assertEqual(serial_log, helper_serial_action(i))
            self.serial._receivedData = ""


        self.instrument.stop()




unittest.main()
