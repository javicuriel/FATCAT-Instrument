#!/usr/bin/env python
# Created by Javier Curiel
# Copyright (c) 2018 Javier Curiel. All rights reserved.

from Models import Topic
from Models import Message
from Models import IModule
from uuid import getnode as get_mac
import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports
import time, os, psutil, datetime
import logging


MQTT_TYPE_READING = 'reading'
MQTT_TYPE_MODULE = 'modules'

Topic.create_table(True)
Message.create_table(True)

# logging.getLogger('instrument').addHandler(logging.NullHandler())
# logging.basicConfig(format=LOG_FORMAT,datefmt=DATE_FORMAT, filename='instrument.log', level=logging.DEBUG)
# logging.basicConfig(filename='instrument.log', level=logging.DEBUG)

class Instrument(object):

    # __slots__ = 'uuid','mqtt_host','mqtt_port','mqtt_keep_alive','mqtt_qos','_mqtt_publish_topic','serial_port_description','serial_baudrate','serial_parity','serial_stopbits','serial_bytesize','serial_timeout','_mqtt_connected','_mqtt_clean_session','_mqtt_retain','_mqtt_messages_lost','_mqtt_client','_serial','_imodules','date_format'

    def __init__(self, date_format = '%Y-%m-%d %H:%M:%S', *args, **kwargs ):
        super(Instrument, self).__init__()
        self.uuid = str(get_mac())

        self.mqtt_host = kwargs.get('mqtt_host')
        self.mqtt_port = kwargs.get('mqtt_port')
        self.mqtt_keep_alive = kwargs.get('mqtt_keep_alive')
        self.mqtt_qos = kwargs.get('mqtt_qos')
        self.mqtt_publish_topic = ''

        self.serial_port_description = kwargs.get('serial_port_description')
        self.serial_baudrate = kwargs.get('serial_baudrate')
        self.serial_parity = kwargs.get('serial_parity')
        self.serial_stopbits = kwargs.get('serial_stopbits')
        self.serial_bytesize = kwargs.get('serial_bytesize')
        self.serial_timeout = kwargs.get('serial_timeout')

        self._mqtt_connected = False
        self._mqtt_clean_session = False
        self._mqtt_retain = False
        self._mqtt_messages_lost = False
        self._mqtt_resend_from_db = True

        self._mqtt_client = self._setup_mqtt_client()
        # self._serial = self._set_up_serial()
        self._serial = None
        self._imodules = {}

        self.date_format = date_format
        self.log_format = '%(asctime)s [%(levelname)s] %(instrument_uuid)s - %(module_name)s :: %(message)s'

        # self._log_extra = {'instrument_uuid': self.uuid, 'module_name': ''}
        # self._logger = logging.getLogger('instrument')
        # self._logger = logging.LoggerAdapter(self._logger, self._log_extra)


    def _setup_mqtt_client(self):
        # Creates MQTT client
        client = mqtt.Client(
            client_id = self.uuid,
            clean_session = self._mqtt_clean_session
        )

        client.connect_async(
            host = self.mqtt_host,
            port = self.mqtt_port,
            keepalive = self.mqtt_keep_alive
        )

        # Sets callback functions for message arrival
        client.on_connect = self._mqtt_on_connect
        client.on_disconnect = self._mqtt_on_disconnect

        # Callback is global because client will only subscribe to current modules
        all_module_topic = self._create_topic(topic_type = MQTT_TYPE_MODULE, t = '#')
        client.message_callback_add(all_module_topic.value, self._on_module_message)

        return client


    def _set_up_serial(self):
        # Waits 2 seconds before trying again if no port found
        # and doubles time each try with maximum 32 second waiting time
        port = self._lookup_port()
        wait = 2

        while not port:
             print("No TCA found, waiting " + str(wait) + " seconds...")
             time.sleep(wait)
             if wait < 32:
                 wait = wait*2
             port = self._lookup_port()

        print("Serial port found: " + port.device)
        return serial.Serial(
            port = port.device,
            baudrate = self.serial_baudrate,
            parity = self.serial_parity,
            stopbits = self.serial_stopbits,
            bytesize = self.serial_bytesize,
            timeout = self.serial_timeout
        )

    def _lookup_port(self):
        # Looks for and returns port with description
        ports = serial.tools.list_ports.comports()
        for port in ports:
            return port if self.serial_port_description in port else None


    def _on_module_message(self, client, userdata, message):
        # Topic format
        # {id}/modules/{module_name}/{action}
        module_name = message.topic.split('/')[2]
        try:
            self._imodules[module_name].run_action(str(message.payload))
        except Exception as e:
            print(e)
            # self._log_extra['module_name'] = module_name
            # self._logger('Action done:' +str(message.payload))

    def read_data(self):
        # Read data from serial
        if not self._serial:
            raise ValueError('Serial is not set!')

        return self._serial.readline().rstrip('\n')

    def _mqtt_on_connect(self, *args, **kwargs):
        # Set _mqtt_connected flag to true
        self._mqtt_connected = True

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        for imodule in self._imodules:
            topic = self._create_topic(topic_type = MQTT_TYPE_MODULE, t=imodule)
            self._mqtt_client.subscribe(topic.value, self.mqtt_qos)


    def _mqtt_on_disconnect(self, *args, **kwargs):
        # Set _mqtt_connected flag to false
        self._mqtt_connected = False

    def _mqtt_send_crash_messages(self):
        # Run aplication on start up, resends messages not recieved
        if self._mqtt_resend_from_db:
            messages = Message.select().where(Message.sent == False)
            for msg in messages:
                self._mqtt_publish(msg)
            self._mqtt_resend_from_db = False

    def _mqtt_send_lost_messages(self):
        # If client is connected and a message was lost then send all messages that where not received
        if self._mqtt_connected and self._mqtt_messages_lost and not self._mqtt_client._out_messages:
            Message.update({Message.sent: True}).where(Message.sent == False).execute()
            self._mqtt_messages_lost = False
            self._mqtt_send_crash_messages()

    def _mqtt_publish(self, msg):
        # Publish the message to the server and store result in msg_info
        msg_info = self._mqtt_client.publish(msg.topic.value, str(msg.timestamp) +'\t'+ msg.payload, qos = self.mqtt_qos, retain = self._mqtt_retain)

        # If sent is successful, set sent flag to true
        if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
            msg.sent = True
        else:
            self._mqtt_messages_lost = True

        # Save the message in the local database
        if self.mqtt_qos > 0:
            msg.save()

        return msg.sent

    def _create_topic(self, topic_type, t = ''):
        # Creates topic with format:
        # {id}/{topic_type}/{val}
        final_value = self.uuid + '/' + topic_type
        if t:
            final_value += '/' + t
        topic, _ = Topic.get_or_create(value = final_value)
        return topic

    @property
    def mqtt_publish_topic(self):
        return self._mqtt_publish_topic

    @mqtt_publish_topic.setter
    def mqtt_publish_topic(self, value):
        self._mqtt_publish_topic = self._create_topic(topic_type = MQTT_TYPE_READING)

    def add_module(self, imodule):
        if imodule.name in self._imodules.keys():
            raise ValueError(imodule.name + ' already exists! Modules cannot have the same name.')

        imodule.serial = self._serial
        self._imodules[imodule.name] = imodule

    def get_module(self, name):
        return self._imodules[name]

    def start(self, test = False):
        # Starts async MQTT client, sends lost messages when connected and starts reading data
        self._mqtt_client.loop_start()
        self._mqtt_send_crash_messages()
        if not test:
            print("Starting reader...")
            self.start_reader()

    def _get_timestamp(self):
        # Return timestamp with user set format
        return datetime.datetime.now().strftime(self.date_format)

    def start_reader(self):
        process = psutil.Process(os.getpid())
        wait = 0.25
        start = time.time()
        while(True):
            end = time.time()
            mb = process.memory_info().rss/1000000
            if (end - start) > 2:
                mb = process.memory_info().rss/1000000
                start = time.time()
            try:
                print(str(mb) + ' mb ' + str(len(self._mqtt_client._out_messages)))
                # os.system( 'clear' )
                self._mqtt_send_lost_messages()
                data = self.read_data()
                timestamp = self._get_timestamp()
                message = Message(topic = self.mqtt_publish_topic, payload = data, timestamp = timestamp)
                self._mqtt_publish(message)

            except Exception as e:
                print(e)
            time.sleep(wait)

    def start_reader_final(self):
        while(True):
            try:
                self._mqtt_send_lost_messages()
                data = self.read_data()
                timestamp = self._get_timestamp()
                message = Message(topic = self.mqtt_publish_topic, payload = data, timestamp = timestamp)
                self._mqtt_publish(message)
            except Exception as e:
                print(e)
                time.sleep(5)

    def stop(self):
        self._mqtt_client.loop_stop()
        self._serial.close()
