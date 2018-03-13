import unittest
from Instrument import *
import os, pty
import paho.mqtt.publish as publish
from SerialEmulator import *
import time

MQTT_SERVER = 'localhost'
MQTT_QOS = 1
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_CLEAN_SESSION = False

SERIAL_PORT_DESCRIPTION = 'nano-TD'
SERIAL_BAUDRATE = 115200,
SERIAL_PARITY = serial.PARITY_NONE,
SERIAL_STOPBITS = serial.STOPBITS_ONE,
SERIAL_BYTESIZE = serial.EIGHTBITS,
SERIAL_TIMEOUT = 1

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


def helper_serial_action(value):
    return str(int(value) + 10)

class MqttMessageEmulator(object):
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


class ModuleTest(unittest.TestCase):
    def setUp(self):
        self.name = 'ModuleTest'
        self.test_module = IModule(name = self.name)
        self.test_action = 'test_on'
        self.test_serial_action = 'test_serial_on'
        self.test_module.set_action(self.test_action, self.test_serial_action)
        self.serial = SerialEmulator()
        self.test_module.serial = self.serial

    def testAction(self):
        self.test_module.run_action(self.test_action)
        serial_log = self.serial._receivedData
        self.assertEqual(serial_log, self.test_serial_action)

    def testActionNoSerial(self):
        self.test_module.serial = None
        self.assertRaises(ValueError, self.test_module.run_action,self.test_action)


class InstrumentTest(unittest.TestCase):
    def setUp(self):

        # Instrument creation
        self.instrument = Instrument(
            mqtt_host = MQTT_SERVER,
            mqtt_port = MQTT_PORT,
            mqtt_keep_alive = MQTT_KEEPALIVE,
            mqtt_qos = MQTT_QOS,
        )

        self.serial = SerialEmulator()
        self.instrument._serial = self.serial
        self.test_messages = 1
        self.instrument.scheduler.remove_jobstore('default')
        self.instrument.scheduler.add_jobstore('sqlalchemy', url='sqlite:///TestJobs.db')

    def testRead(self):
        module_read = self.instrument._read_data()
        serial_read = self.serial.readline()
        # New reading must show on next serial read
        self.assertNotEqual(serial_read, module_read)

    def testModuleOperationStaticAction(self):
        test_module = IModule(name = 'test_module')
        action, serial_action = 'action', 'serial_action'
        test_module.set_action(action, serial_action)

        self.instrument.add_module(test_module)
        self.instrument.start(test = True)

        topic = self.instrument.uuid + '/modules/'+ test_module.name
        mqtt_msg = MqttMessageEmulator(topic, action)

        # Called when mqtt message is recieved
        self.instrument._on_module_message(None, None, mqtt_msg)
        serial_log = self.serial._receivedData
        # Assert that serial recieved corresponding action
        self.assertEqual(serial_log, serial_action)

    def testModuleOperationRangeAction(self):
        test_module = IModule(name = 'test_module')
        action, serial_action = 'action', 'SA0000-SA0600'
        value = 100
        test_module.set_action(action, serial_action)

        self.instrument.add_module(test_module)
        self.instrument.start(test = True)

        topic = self.instrument.uuid + '/modules/'+ test_module.name
        mqtt_msg = MqttMessageEmulator(topic, action +'='+ str(value))

        # Called when mqtt message is recieved
        self.instrument._on_module_message(None, None, mqtt_msg)
        serial_log = self.serial._receivedData
        # Assert that serial recieved corresponding action
        # self.assertEqual(serial_log, serial_action)
        self.assertEqual(serial_log, 'SA0'+str(value))


    # Functional testing
    def _testModuleOperationStaticAction(self):
        test_module = IModule(name = 'test_module')
        self.instrument.add_module(test_module)
        self.instrument.start(test = True)

        # Helper topic
        topic = self.instrument.uuid + '/modules/'+ test_module.name

        for i in range(self.test_messages):
            # Action sent by MQTT
            action = str(i)
            # Serial Action that should be executed with MQTT action
            serial_action = 'serial_action_' + str(i)
            # Add operable action to module
            test_module.set_action(action, serial_action)
            # Publish MQTT message with the action
            helper_publish(topic, action)
            # Get Serial log
            # Wait to MQTT message arrive
            time.sleep(.005)
            serial_log = self.serial._receivedData
            # Assert that an action sent by MQTT executed the right serial action
            self.assertEqual(serial_log, serial_action)
            self.serial._receivedData = ""

        self.instrument.stop()

    # Functional testing
    def _testModuleOperationDynamicAction(self):
        test_module = IModule(name = 'test_module')
        self.instrument.add_module(test_module)
        self.instrument.start(test = True)

        topic = self.instrument.uuid + '/modules/'+ test_module.name

        for i in range(self.test_messages):
            # Action sent by MQTT
            action_name = 'value'
            # Add operable action to module (Custom user function)
            test_module.set_action(action_name, helper_serial_action)
            # Publish MQTT message with the action
            # Format {id}/modules/{action_name}={value}
            helper_publish(topic, action_name + '=' + str(i))
            # Get Serial log
            # Wait to MQTT message arrive
            time.sleep(.005)
            serial_log = self.serial._receivedData
            # Assert that an action sent by MQTT executed the right serial action
            self.assertEqual(serial_log, helper_serial_action(i))
            self.serial._receivedData = ""


        self.instrument.stop()




unittest.main()
