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

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


MQTT_TYPE_READING = 'reading'
MQTT_TYPE_MODULE = 'modules'
MQTT_TYPE_STATUS = 'status'

Topic.create_table(True)
Message.create_table(True)

SingletonInstrument = None

def run_job(event_name):
    SingletonInstrument.run_job(event_name)

def convert_to_seconds(value, unit):
    seconds = 1
    minutes = 60
    hours = 3600
    days = 86400
    return value*eval(unit)

class InstrumentLogHandler(object):
    def __init__(self, topic, instrument):
        super(InstrumentLogHandler, self).__init__()
        self.instrument = instrument
        self._topic = topic

    def write(self, string):
        sys.stdout.write(string)
        if self.instrument._mqtt_connected and self.instrument._log_info['send_mqtt']:
            self.instrument._mqtt_client.publish(topic = self._topic.value, payload = string, qos = self.instrument.mqtt_qos, retain = self.instrument._mqtt_retain)

    def flush(self):
        sys.stdout.flush()


class Instrument(object):

    # __slots__ = 'uuid','mqtt_host','mqtt_port','mqtt_keep_alive','mqtt_qos','_mqtt_publish_topic','serial_port_description','serial_baudrate','serial_parity','serial_stopbits','serial_bytesize','serial_timeout','_mqtt_connected','_mqtt_clean_session','_mqtt_retain','_mqtt_messages_lost','_mqtt_client','_serial','_imodules','date_format'

    def __init__(self, date_format = '%Y-%m-%d %H:%M:%S', *args, **kwargs ):
        super(Instrument, self).__init__()
        self.uuid = str(get_mac())
        self.name = 'instrument'

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

        self._logger = self._setup_logger(self.name)
        self.scheduler = self._set_up_scheduler()

        self._modes = {'ANALYSIS_MODE':None}
        global SingletonInstrument
        SingletonInstrument = self


    def _set_up_scheduler(self):

        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
        }
        scheduler = BackgroundScheduler(jobstores = jobstores)
        scheduler.name = 'apscheduler'
        self._setup_logger(scheduler.name)

        events = self.get_events()
        for event_name, time in events:
            scheduler.add_job(run_job, 'cron', second=time, name=event_name , id=event_name, replace_existing=True, coalesce= False, max_instances= 100, args = [event_name])

        return scheduler

    def _setup_logger(self, name):
        logger = logging.getLogger(name)
        # logger = logging.getLogger('apscheduler')

        logger.setLevel(logging.INFO)

        topic = self._create_topic(topic_type = MQTT_TYPE_STATUS)
        mqtth = InstrumentLogHandler(topic, self)
        # create console handler and set level to debug
        instrument_log_handler = logging.StreamHandler(mqtth)
        fileHandler = logging.FileHandler('{0}.log'.format(self.name))


        # create formatter
        if name == 'apscheduler':
            log_format = '%(asctime)s [%(levelname)s] - Module:scheduler :: %(message)s'
        else:
            log_format = self._log_format

        formatter = logging.Formatter(fmt = log_format, datefmt = self.date_format)

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
        action = str(message.payload)
        self.log_message(module = module_name, msg = "MQTT Message: "+ action, level = logging.DEBUG)
        self.run_action(module_name, action)

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
            self.log_message(module = 'database', msg = 'Resending '+ str(messages.count())+ ' messages')
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
        # TODO
        # Try (*maube)
        return self._imodules[name]

    def get_mode(self, name):
        print(name + " Started")

    def get_events(self):
        return []
        # return [('event_test', '*/3')]

    def run_job(self, name):
        actions = self._jobs[name]

        for action_type, action in actions:
            if action_type == 'mode':
                self.run_mode(action)
            elif action_type == 'module':
                self.run_action(action[0], action[1])
            elif action_type == 'wait':
                time.sleep(convert_to_seconds(int(action[0]),action[1]))
            else:
                raise ValueError("Invalid action type:" + action_type)

    def run_mode(self, name):
        actions = self._modes[name]
        self.log_message(module = "instrument", msg = "Started mode: " + name)
        for module, action in actions:
            if not self.run_action(module, action):
                return False
        self.log_message(module = "instrument", msg = "Mode executed successfully: " + name)
        return True

    def set_job(self, name, actions):
        tuple_actions = self._get_tuple_actions(self, actions)
        if tuple_actions:
            self._jobs[name] = tuple_actions
            status = "Job saved successfully: "+ name
            level = logging.INFO
        else:
            status = "Job not added: " + name
            level = logging.WARNING
        self.log_message(module = "instrument", msg = status, level = level)

    def set_mode(self, name, actions):
        try:
            tuple_actions = self._get_tuple_actions(self, actions)
            for module, action in actions:
                self._imodules[module].validate_action(action)
            self._modes[name] = tuple_actions
            status = "Mode saved successfully: "+ name
            level = logging.INFO
        except Exception as e:
            status = str(e) + " :: Mode not added: " + name
            level = logging.ERROR
        self.log_message(module = "instrument", msg = status, level = level)

    def _get_tuple_actions(self, actions):
        # Gets actions list and converts it to tuples list
        tuple_actions = []
        try:
            for a in actions:
                action = a.split(':')
                if len(action) < 2 or len(action) > 3:
                    raise ValueError("Invalid action format: " + action)
                tuple_actions.append((action[0], action[1], action[2] if len(action) == 3 else None))
        except Exception as e:
            tuple_actions = None
            self.log_message(module = "instrument", msg = str(e), level = logging.ERROR)
        return tuple_actions


    def run_action(self, module, action):
        serial_action = None
        try:
            serial_action = self._imodules[module].run_action(action)
            status = action + " executed the command " + serial_action + " successfuly."
            level = logging.INFO
        except Exception as e:
            status = str(e)
            level = logging.ERROR
        self.log_message(module = module, msg = status, level = level)

        return True if serial_action else False




    def start(self, test = False):
        # Starts async MQTT client, sends lost messages when connected and starts reading data
        self._mqtt_client.loop_start()
        self._mqtt_send_crash_messages()
        self.scheduler.start()
        self._memory_usage()
        if not test:
            self.log_message(module = MQTT_TYPE_READING, msg = "Starting reader on topic = "+ self.mqtt_publish_topic.value)
            self.start_reader()

    def _get_timestamp(self):
        # Return timestamp with user set format
        return datetime.datetime.now().strftime(self.date_format)

    def _memory_usage(self):
        process = psutil.Process(os.getpid())
        mb = process.memory_info().rss/1000000
        self.log_message(module = 'memory', msg = str(mb)+ ' mb', level = logging.INFO)

    def start_reader(self):
        while(True):
            try:
                self._mqtt_send_lost_messages()
                data = self._read_data()
                timestamp = self._get_timestamp()
                message = Message(topic = self.mqtt_publish_topic, payload = data, timestamp = timestamp)
                self._mqtt_publish(message)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.log_message(module = MQTT_TYPE_READING, msg = str(e), level = logging.ERROR)
                self._memory_usage()
                time.sleep(5)

    def stop(self):
        self._mqtt_client.loop_stop()
        self.log_message(module = 'mqttclient', msg = "stopped")
        self._serial.close()
        self.log_message(module = 'serial', msg = "closed")
        self.scheduler.shutdown()
