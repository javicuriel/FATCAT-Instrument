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
import sys


MQTT_TYPE_READING = 'reading'
MQTT_TYPE_MODULE = 'modules'
MQTT_TYPE_STATUS = 'status'

Topic.create_table(True)
Message.create_table(True)


class InstrumentLogHandler(object):
    def __init__(self, topic, instrument):
        super(InstrumentLogHandler, self).__init__()
        self.instrument = instrument
        self._topic = topic

    def write(self, string):
        sys.stderr.write(string)
        if self.instrument._mqtt_connected and self.instrument._log_info['send_mqtt']:
            self.instrument._mqtt_client.publish(topic = self._topic.value, payload = string, qos = self.instrument.mqtt_qos, retain = self.instrument._mqtt_retain)

    def flush(self):
        sys.stderr.flush()


class Instrument(object):

    # __slots__ = 'uuid','mqtt_host','mqtt_port','mqtt_keep_alive','mqtt_qos','_mqtt_publish_topic','serial_port_description','serial_baudrate','serial_parity','serial_stopbits','serial_bytesize','serial_timeout','_mqtt_connected','_mqtt_clean_session','_mqtt_retain','_mqtt_messages_lost','_mqtt_client','_serial','_imodules','date_format'

    def __init__(self, date_format = '%Y-%m-%d %H:%M:%S', debug = False, *args, **kwargs ):
        super(Instrument, self).__init__()
        self.uuid = str(get_mac())
        self.name = 'Instrument'

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
        self._log_format = '%(asctime)s [%(levelname)s] %(message)s'
        self._log_info = {}

        self._logger = self._setup_logger(debug)

    def _setup_logger(self, debug):
        level = logging.INFO
        if debug:
            level = logging.DEBUG

        logger = logging.getLogger(self.name)
        logger.setLevel(level)

        topic = self._create_topic(topic_type = MQTT_TYPE_STATUS)
        mqtth = InstrumentLogHandler(topic, self)
        # create console handler and set level to debug
        instrument_log_handler = logging.StreamHandler(mqtth)
        instrument_log_handler.setLevel(level)

        fileHandler = logging.FileHandler('{0}.log'.format(self.name))


        # create formatter
        formatter = logging.Formatter(fmt = self._log_format, datefmt = self.date_format)

        # add formatter to ch
        instrument_log_handler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(instrument_log_handler)
        logger.addHandler(fileHandler)
        logger = logging.LoggerAdapter(logger, self._log_info)

        return logger


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
        # {id}/modules/{module_name} payload={action}
        module_name = message.topic.split('/')[2]
        self.log_message(module = module_name, msg = "MQTT Message: "+ str(message.payload), level = logging.DEBUG)
        try:
            serial_action = self._imodules[module_name].run_action(str(message.payload))
            status = str(message.payload) + " executed the command " + serial_action + " successfuly."
            level = logging.INFO
        except Exception as e:
            status = str(e)
            level = logging.ERROR
        self.log_message(module = module_name, msg = status, level = level)

    def _read_data(self):
        # Read data from serial
        if not self._serial:
            raise ValueError('Serial is not set!')

        return self._serial.readline().rstrip('\n')


    def log_message(self, module, msg, level = logging.INFO, send_mqtt = True):
        log_message = "- Module:{0} :: {1}"
        log_message = log_message.format(module,msg)

        self._log_info['send_mqtt'] = send_mqtt
        self._logger.log(level,log_message)

    def _mqtt_on_connect(self, *args, **kwargs):
        # Set _mqtt_connected flag to true
        self._mqtt_connected = True
        self.log_message(module = 'MQTTClient', msg = 'connected to '+ self.mqtt_host)

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        for imodule in self._imodules:
            topic = self._create_topic(topic_type = MQTT_TYPE_MODULE, t=imodule)
            self._mqtt_client.subscribe(topic.value, self.mqtt_qos)
            self.log_message(module = 'MQTTClient', msg = 'Subscribe to '+ imodule, level = logging.DEBUG)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        # Set _mqtt_connected flag to false
        self._mqtt_connected = False
        self.log_message(module = 'MQTTClient', msg = 'disconnected')

    def _mqtt_send_crash_messages(self):
        # Run aplication on start up, resends messages not recieved
        if self._mqtt_resend_from_db:
            messages = Message.select().where(Message.sent == False)
            self.log_message(module = 'DB', msg = 'Resending '+ str(messages.count())+ ' messages')
            for msg in messages:
                self._mqtt_publish(msg)
            self._mqtt_resend_from_db = False

    def _mqtt_send_lost_messages(self):
        # If client is connected and a message was lost then send all messages that where not received
        if self._mqtt_connected and self._mqtt_messages_lost and not self._mqtt_client._out_messages:
            count = Message.update({Message.sent: True}).where(Message.sent == False).execute()
            self._mqtt_messages_lost = False
            self.log_message(module = 'DB', msg = 'Sent '+ str(count)+ ' messages')


    def _mqtt_publish(self, msg):
        # Publish the message to the server and store result in msg_info
        msg_info = self._mqtt_client.publish(msg.topic.value, str(msg.timestamp) +'\t'+ msg.payload, qos = self.mqtt_qos, retain = self._mqtt_retain)

        # If sent is successful, set sent flag to true
        if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
            msg.sent = True
            mqtt_err = '[MQTT_ERR_SUCCESS]'
        else:
            self._mqtt_messages_lost = True
            if msg_info.rc == mqtt.MQTT_ERR_NO_CONN:
                mqtt_err = '[MQTT_ERR_NO_CONN]'
            elif msg_info.rc == mqtt.MQTT_ERR_QUEUE_SIZE:
                mqtt_err = '[MQTT_ERR_QUEUE_SIZE]'

        # Log
        self.log_message(module = MQTT_TYPE_READING + ' - ' +mqtt_err, msg = msg.payload.replace("\t", " "), level = logging.DEBUG ,send_mqtt = False)

        # Save the message in the local database
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
            msg = imodule.name + ' already exists! Modules cannot have the same name.'
            self.log_message(module = "Instrument", msg = msg, level = logging.CRITICAL, send_mqtt = False)
            raise ValueError(msg)

        imodule.serial = self._serial
        self._imodules[imodule.name] = imodule

    def get_module(self, name):
        return self._imodules[name]

    def start(self, test = False):
        # Starts async MQTT client, sends lost messages when connected and starts reading data
        self._mqtt_client.loop_start()
        self._mqtt_send_crash_messages()
        if not test:
            self.start_reader()

    def _get_timestamp(self):
        # Return timestamp with user set format
        return datetime.datetime.now().strftime(self.date_format)

    def start_reader(self):
        self.log_message(module = MQTT_TYPE_READING, msg = "Starting reader on topic = "+ self.mqtt_publish_topic.value)
        start = time.time()
        process = psutil.Process(os.getpid())
        while(True):
            end = time.time()
            mb = process.memory_info().rss/1000000
            if (end - start) > 2:
                mb = process.memory_info().rss/1000000
                start = time.time()
            try:
                # print(str(mb) + ' mb ' + str(len(self._mqtt_client._out_messages)))
                # os.system( 'clear' )
                self._mqtt_send_lost_messages()
                data = self._read_data()
                timestamp = self._get_timestamp()
                message = Message(topic = self.mqtt_publish_topic, payload = data, timestamp = timestamp)
                self._mqtt_publish(message)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                status = str(e)
                self.log_message(module = MQTT_TYPE_READING, msg = status, level = logging.ERROR)
                time.sleep(10)

    def start_reader_final(self):
        while(True):
            try:
                self._mqtt_send_lost_messages()
                data = self._read_data()
                timestamp = self._get_timestamp()
                message = Message(topic = self.mqtt_publish_topic, payload = data, timestamp = timestamp)
                self._mqtt_publish(message)
            except Exception as e:
                print(e)
                time.sleep(5)

    def stop(self):
        self._mqtt_client.loop_stop()
        self.log_message(module = 'MQTTClient', msg = "stopped")
        self._serial.close()
        self.log_message(module = 'Serial', msg = "closed")
