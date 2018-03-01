#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
from models import *
import time
import sys
from uuid import getnode as get_mac

# Client ID to MQTT Server
# Port 1883 not encrypted
# Quality of service = 1, meaning the server must receive the message at least once

CLIENT_ID = 'testmacbook'
SERVER = 'localhost'
QOS = 1
PORT = 1883
KEEPALIVE = 60
CLEAN_SESSION = False
SEND_SAVED_TIME = 2

class Instrument(mqtt.Client):
    # Example of slots use

    # __slots__ = 'timestamp', 'state', 'dup', 'mid', '_topic', 'payload', 'qos', 'retain', 'info'
    
    def __init__(self, *args, **kwargs):
        super(Instrument, self).__init__()
        self.uuid = get_mac()

        self.mqtt_host = kwargs.get('mqtt_host')
        self.mqtt_port = kwargs.get('mqtt_port')
        self.mqtt_keep_alive = kwargs.get('mqtt_keep_alive')
        self.mqtt_qos = kwargs.get('mqtt_qos')
        self.mqtt_lost_messages_retry_time = kwargs.get('mqtt_lost_messages_retry_time')

        self._mqtt_connected = False
        self._mqtt_message_lost = False
        self._mqtt_clean_session = False
        self._mqtt_retain = False
        self._mqtt_topics = None

        self._mqtt_client = self._setup_mqtt_client()

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


    def set_topics(self, *args):
        self.topics = args

    def _mqtt_on_connect(self, *args, **kwargs):
        # Set _mqtt_connected flag to true
        self._mqtt_connected = True

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        map(lambda topic: self._mqtt_client.subscribe(topic, self.mqtt_qos), self.topics)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        # Set _mqtt_connected flag to false
        self._mqtt_connected = False

    def _mqtt_send_lost_messages(self):
        # If client is connected and a message was lost then send all messages that where not received
        if self._mqtt_connected and self._mqtt_message_lost:
            messages = Message.select().where(Message.sent == False)
            self._mqtt_message_lost = not all(map(self.save_publish, messages))


    def _mqtt_publish(self, msg):
        # Publish the message to the server and store result in msg_info
        msg_info = self.publish(msg.topic, msg.payload, qos = self.mqtt_qos, retain = self._mqtt_retain)

        # If sent is successful, set sent flag to true
        if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
            msg.sent = True
        else:
            self._mqtt_message_lost = True

        # Save the message in the local database
        if self.mqtt_qos > 0:
            msg.save()

        return msg.sent

    def start(self):
        # Create database if none exists
        if self.mqtt_qos > 0:
            Message.create_table(True)
        mqtt_client.loop_start()



def publish(client, msg):
    # Publish the message to the server and store result in msg_info
    msg_info = client.publish(msg.topic, msg.payload, qos=QOS, retain=False)

    # If sent is successful, set sent flag to true
    if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
        msg.sent = True

    # Save the message in the local database
    msg.save()



# The callback for when the client receives a CONNACK response from the server.
def on_connect(self, userdata, flags, rc):
    # Set is_connected flag to true
    self.userdata.is_connected = True

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    self.subscribe("sensors/light/2/switch",1)


def on_publish(client, userdata, mid):
    pass


def on_disconnect(self, userdata, rc):
    # Set is_connected flag to false
    self.userdata.is_connected = False


def send_saved_messages(client):
    # If client is connected then send all messages that where not received
    if client.userdata.is_connected:
        messages = Message.select().where(Message.sent == False)
        for msg in messages:
            publish(client, msg)




start = time.time()
userdata = Userdata()
client = mqtt.Client(CLIENT_ID, clean_session=CLEAN_SESSION)
client.userdata = userdata
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.connect_async(SERVER, PORT, KEEPALIVE)
client.loop_start()
Message.create_table(True)

instrument = Instrument(mqtt_host = 'localhost', mqtt_port = 1883, mqtt_keep_alive = 60, mqtt_qos = 1, mqtt_lost_messages_retry_time = 2)
# instrument.start()

datafile = "SampleData.txt"
fi = open(datafile, "r")

start = time.time()

for i,line in enumerate(fi):
   if (i > 2):
       end = time.time()
       if (end - start) > SEND_SAVED_TIME:
           start = time.time()
           send_saved_messages(client)
       datastring = line.rstrip('\n')
       msg = Message(topic = "data_test", payload = datastring)
       publish(client, msg)
       print(datastring)
       time.sleep(0.25)
   else:
       i += 1
fi.close()
client.loop_stop()
