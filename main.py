#!/usr/bin/env python
# by Javier Curiel

import paho.mqtt.client as mqtt
import time
from models import *
from uuid import getnode as get_mac


# Port 1883 not encrypted
# Quality of service = 1, meaning the server must receive the message at least once
MQTT_SERVER = 'localhost'
MQTT_QOS = 1
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_CLEAN_SESSION = False
MQTT_SEND_LOST_TIME = 2

MQTT_TYPE_READING = 'reading'
MQTT_TYPE_MODULE = 'modules'


class Instrument(object):

    def __init__(self, *args, **kwargs):
        super(Instrument, self).__init__()
        self.uuid = str(get_mac())

        self.mqtt_host = kwargs.get('mqtt_host')
        self.mqtt_port = kwargs.get('mqtt_port')
        self.mqtt_keep_alive = kwargs.get('mqtt_keep_alive')
        self.mqtt_qos = kwargs.get('mqtt_qos')
        self.mqtt_lost_messages_retry_time = kwargs.get('mqtt_lost_messages_retry_time')
        self.mqtt_publish_topic = ''

        self._mqtt_connected = False
        self._mqtt_messages_lost = 0
        self._mqtt_clean_session = False
        self._mqtt_retain = False
        self._mqtt_actions = {}


        self._mqtt_client = self._setup_mqtt_client()

        self._imodules = {}


    def _setup_mqtt_client(self):
        client = mqtt.Client(
            client_id = self.uuid,
            clean_session = self._mqtt_clean_session
        )

        client.connect_async(
            host = self.mqtt_host,
            port = self.mqtt_port,
            keepalive = self.mqtt_keep_alive
        )

        client.on_connect = self._mqtt_on_connect
        client.on_disconnect = self._mqtt_on_disconnect

        return client

    def add_module(self, imodule):
        if imodule.name in self._imodules.keys():
            raise ValueError(imodule.name + ' already exists! Modules cannot have the same name.')

        self._imodules[imodule.name] = imodule

    def set_callbacks(self):
        all_module_topics = self._create_topic('#', MQTT_TYPE_MODULE)
        self._mqtt_client.message_callback_add(all_module_topics, self.on_module_action)

    def on_module_action(self, client, userdata, message):
        # Topic structure
        # {id}/modules/{module_name}/{action}
        module_name = message.topic.split('/')[2]
        self._imodules[module_name].run_action(str(message.payload))



    def testPrint(self, p, qos):
        print("Topic: "+ p + " QoS: "+ str(qos))

    def _mqtt_on_connect(self, *args, **kwargs):
        # Set _mqtt_connected flag to true
        self._mqtt_connected = True

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        map(lambda imodule: self.testPrint(self._create_topic(imodule, MQTT_TYPE_MODULE), self.mqtt_qos), self._imodules)
        map(lambda imodule: self._mqtt_client.subscribe(self._create_topic(imodule, MQTT_TYPE_MODULE), self.mqtt_qos), self._imodules)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        # Set _mqtt_connected flag to false
        self._mqtt_connected = False

    def _mqtt_send_lost_messages(self):
        # If client is connected and a message was lost then send all messages that where not received
        if self._mqtt_connected and self._mqtt_messages_lost and not self._mqtt_client._out_messages:
            print(self._mqtt_messages_lost)
            messages = Message.select().where(Message.sent == False)
            for msg in messages:
                self._mqtt_messages_lost -= 1 if self._mqtt_publish(msg) and self._mqtt_messages_lost else 0

    def _mqtt_publish(self, msg):
        # Publish the message to the server and store result in msg_info
        msg_info = self._mqtt_client.publish(msg.topic, msg.payload, qos = self.mqtt_qos, retain = self._mqtt_retain)

        # If sent is successful, set sent flag to true
        if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
            msg.sent = True

        # Save the message in the local database
        if self.mqtt_qos > 0:
            msg.save()

        return msg.sent

    # def _mqtt_add_subscribe_topics(self, topic):
    #     self._mqtt_topics

    def _create_topic(self, topic, topic_type):
        return self.uuid + '/' + topic_type + '/' + topic

    @property
    def mqtt_publish_topic(self):
        return self._mqtt_publish_topic

    @mqtt_publish_topic.setter
    def mqtt_publish_topic(self, value):
        self._mqtt_publish_topic = self._create_topic(value, MQTT_TYPE_READING)
        # self._mqtt_publish_topic = self._add_uuid(value)


    def start(self):
        # Create database if none exists
        if self.mqtt_qos > 0:
            Message.create_table(True)
            self._mqtt_messages_lost = Message.select().where(Message.sent == False).count()
        self.set_callbacks()
        self._mqtt_client.loop_start()
        self.read_from_file()

    def read_from_file(self):
        datafile = "SampleData.txt"
        fi = open(datafile, "r")
        fi = fi.readlines()[3:]
        start = time.time()
        for line in fi:
            end = time.time()
            if (end - start) > self.mqtt_lost_messages_retry_time:
                start = time.time()

                self._mqtt_send_lost_messages()
            datastring = line.rstrip('\n')
            msg = Message(topic = self.mqtt_publish_topic, payload = datastring)
            self._mqtt_messages_lost += 1 if not self._mqtt_publish(msg) else 0
            # print(datastring)
            time.sleep(0.25)
        fi.close()
        client.loop_stop()


def togglePump(self):
    # find out which serial port is connected
    ser = open_tca_port()
    if self.statusVarsData.pump[-1]:
        ser.write('U0000')
    else:
        ser.write('U1000')
    ser.close()

def toggle(imodule):
    # find out which serial port is connected
    ser = imodule.port
    if self.statusVarsData.pump[-1]:
        ser.write(imodule.off)
    else:
        ser.write(imodule.on)
    ser.close()

def set_valuex(value):
    return "entro" + str(value)

def test(value):
    print(value)


pump = IModule(name = 'pump', port = 'test_port')

pump.set_action('on', 'U1000')
pump.set_action('off', 'U0000')
pump.set_action('set_value', set_valuex)

instrument = Instrument(
    mqtt_host = MQTT_SERVER,
    mqtt_port = MQTT_PORT,
    mqtt_keep_alive = MQTT_KEEPALIVE,
    mqtt_qos = MQTT_QOS,
    mqtt_lost_messages_retry_time = MQTT_SEND_LOST_TIME,
)
instrument.add_module(pump)

instrument.start()
