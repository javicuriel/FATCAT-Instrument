#!/usr/bin/env python
# Created by Javier Curiel
# Copyright (c) 2018 Javier Curiel. All rights reserved.

from models import Topic
from models import Message
from models import IModule
from uuid import getnode as get_mac
import paho.mqtt.client as mqtt
import serial
import serial.tools.list_ports
import time, os, psutil, datetime
import logging
import sys
import gc
import ssl
import json
import helpers
import peewee as pw
import numpy as np


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


MQTT_TYPE_READING = 'iot-2/evt/reading'
MQTT_TYPE_ANALYSIS = 'iot-2/evt/analysis'
MQTT_TYPE_JOBS = 'iot-2/evt/jobs'
MQTT_TYPE_MODULE = 'iot-2/cmd'
MQTT_TYPE_STATUS = 'status'

Topic.create_table(True)
Message.create_table(True)

SingletonInstrument = None

def memory_info():
    SingletonInstrument.memory_usage()


def helper_run_job(event_name, actions):
    # Helper function tu run a job
    SingletonInstrument._run_actions(event_name, actions)

def convert_to_seconds(unit, value):
    """
    Converts an number to seconds
    ej. convert_to_seconds('minutes', 5) => 300
    """
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
        # if self.instrument._mqtt_connected and self.instrument._log_info['send_mqtt']:
        #     self.instrument._mqtt_client.publish(topic = self._topic.value, payload = string, qos = self.instrument.mqtt_qos, retain = self.instrument._mqtt_retain)

    def flush(self):
        sys.stdout.flush()


class Instrument(object):

    # __slots__ = 'uuid','mqtt_host','mqtt_port','mqtt_keep_alive','mqtt_qos','_mqtt_publish_topic','serial_port_description','serial_baudrate','serial_parity','serial_stopbits','serial_bytesize','serial_timeout','_mqtt_connected','_mqtt_clean_session','_mqtt_retain','_mqtt_messages_lost','_mqtt_client','_serial','_imodules','date_format'

    def __init__(self, date_format = '%Y-%m-%d %H:%M:%S', *args, **kwargs ):
        super(Instrument, self).__init__()
        global SingletonInstrument
        if SingletonInstrument and not kwargs.get('serial_emulator'):
            raise ValueError("SingletonInstrument already set")

        self.name = 'instrument'
        self.uuid = os.environ["MQTT_UUID"]

        self.mqtt_org = kwargs.get('mqtt_org')
        self.mqtt_host = kwargs.get('mqtt_host')
        self.mqtt_port = kwargs.get('mqtt_port')
        self.mqtt_keep_alive = kwargs.get('mqtt_keep_alive')
        self.mqtt_qos = kwargs.get('mqtt_qos')
        self.mqtt_publish_topic = ''
        self.mqtt_analysis_topic = self._create_topic(topic_type = MQTT_TYPE_ANALYSIS)

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

        # Depending on memory size this is approx 400 MB of memory
        self._mqtt_max_queue = 100000

        self._mqtt_client = self._setup_mqtt_client()

        self._serial = None
        self._imodules = {}

        self.date_format = date_format
        self._log_format = '%(asctime)s [%(levelname)s] %(message)s'
        self._log_info = {}

        self._logger = self._setup_logger(self.name)
        self.scheduler = self._set_up_scheduler()

        self._mqtt_client.enable_logger(logger=self._logger)

        if not kwargs.get('serial_emulator'):
            self._serial = self._set_up_serial()

        self._modes = {}
        SingletonInstrument = self




    def log_message(self, module, msg, level = logging.INFO, send_mqtt = True):
        """
        Logs a message with standard format
        Set send_mqtt to false if MQTT logging is not required
        """
        log_message = "- [{0}] :: {1}"
        log_message = log_message.format(module,msg)
        self._log_info['send_mqtt'] = send_mqtt
        self._logger.log(level,log_message)

    def _set_up_scheduler(self):
        # Creates scheduler with local database and logger
        # returns scheduler
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
        }
        scheduler = BackgroundScheduler(jobstores = jobstores)
        scheduler.name = 'apscheduler'
        self._setup_logger(scheduler.name)
        # scheduler.add_job(memory_info, 'interval', seconds= 60 , name = 'memory', id = 'memory', replace_existing=True)
        return scheduler

    def _setup_logger(self, name):
        # Get logger by name
        logger = logging.getLogger(name)
        # Default level is INFO unless specified by user
        logger.setLevel(logging.INFO)

        # Set log MQTT topic
        topic = self._create_topic(topic_type = MQTT_TYPE_STATUS)
        # Create MQTT-console handler
        mqtth = InstrumentLogHandler(topic, self)

        # Set up MQTT-console and file handler
        instrument_log_handler = logging.StreamHandler(mqtth)
        fileHandler = logging.FileHandler('{0}.log'.format(self.name))

        # Set log format
        if name == 'apscheduler':
            log_format = '%(asctime)s [%(levelname)s] - [scheduler] :: %(message)s'
        else:
            log_format = self._log_format

        # Create formatter
        formatter = logging.Formatter(fmt = log_format, datefmt = self.date_format)

        # Add formatter to handlers
        instrument_log_handler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(instrument_log_handler)
        logger.addHandler(fileHandler)
        # Set logger adapter to pass variables
        # TODO
        # not needed
        logger = logging.LoggerAdapter(logger, self._log_info)

        return logger


    def _setup_mqtt_client(self):
        # Creates MQTT client
        client = mqtt.Client(
            client_id = 'd:{}:{}:{}'.format(self.mqtt_org, self.name, self.uuid),
            protocol= mqtt.MQTTv311,
            clean_session = self._mqtt_clean_session
        )

        client.username_pw_set(
                username='use-token-auth',
                # Should be environment variable
                password= os.environ['IBM_TOKEN']
        )

        # Connection settings
        client.connect_async(
            host = self.mqtt_org + '.' +self.mqtt_host,
            port = self.mqtt_port,
            keepalive = self.mqtt_keep_alive
        )


        # Enable SSL/TLS support.
        if self.mqtt_port == 8883:
            client.tls_set(cert_reqs = ssl.CERT_REQUIRED, tls_version = ssl.PROTOCOL_TLSv1_2)

        # Sets callback functions for message arrival
        client.on_connect = self._mqtt_on_connect
        client.on_disconnect = self._mqtt_on_disconnect

        # Callback is global because client will only subscribe to current modules in function on_connect
        all_module_topic = self._create_topic(topic_type = MQTT_TYPE_MODULE, t = '#')
        client.message_callback_add(all_module_topic.value, self._on_module_message)

        # Set max messages stored in memory
        client.max_queued_messages_set(self._mqtt_max_queue)


        return client


    def _set_up_serial(self):
        # Waits 2 seconds before trying again if no port found
        # and doubles time each try with maximum 32 second waiting time
        port = self._lookup_port()
        wait = 2
        while not port:
            self.log_message(module = "serial", msg = "No TCA found, waiting " + str(wait) + " seconds...", level = logging.WARN)
            time.sleep(wait)
            if wait < 32:
                wait = wait*2
            port = self._lookup_port()

        self.log_message(module = "serial", msg = "Serial port found: " + port.device)
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

    def _job_controller(self, json_command):
        command = json.loads(json_command)
        try:
            if command['action']== 'all':
                self.get_jobs()
            else:
                job = command['job']
                # Add acts as edit as well
                if command['action'] == 'add':
                    targs = helpers.getTriggerArgs(job['trigger'])
                    self.add_job(name = job['id'], actions = job['actions'], **targs)
                elif command['action'] == 'delete':
                    pass
        except Exception as e:
            # TODO Error log
            pass

    def _on_module_message(self, client, userdata, message):
        # Topic format
        # {id}/modules/{module_name}
        # /iot-2/cmd/{module_name}/fmt/txt
        # payload: {action} or {action=99}
        module_name = message.topic.split('/')[2]
        action = str(message.payload)

        if(module_name == 'job'):
            self._job_controller(action)
        else:
            self.log_message(module = 'mqttclient', msg = "MQTT Message: "+module_name+ ":"+ action, level = logging.INFO)
            if(module_name in self._modes):
                self.run_mode(module_name)
            else:
                self.run_action(module_name, action)

    def _mqtt_on_connect(self, *args, **kwargs):
        # Set _mqtt_connected flag to true and log
        self._mqtt_connected = True
        self.log_message(module = 'mqttclient', msg = 'connected to '+ self.mqtt_org + '.' +self.mqtt_host)

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self._mqtt_subscribe(self._imodules)
        self._mqtt_subscribe(self._modes)
        self._mqtt_subscribe({'job'})

    def _mqtt_subscribe(self, topics):
        for t in topics:
            topic = self._create_topic(topic_type = MQTT_TYPE_MODULE, t=t)
            self._mqtt_client.subscribe(topic.value, self.mqtt_qos)
            self.log_message(module = 'mqttclient', msg = 'Subscribe to '+ topic.value, level = logging.DEBUG)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        # Set _mqtt_connected flag to false and log it
        self._mqtt_connected = False
        self.log_message(module = 'mqttclient', msg = 'disconnected '+ mqtt.connack_string(args[2]))


    def _mqtt_resend_from_db(self):
        # Resends messages not recieved from database
        # Should be run on aplication start up
        messages = Message.select().where(Message.sent == False)
        self.log_message(module = 'database', msg = 'Resending '+ str(messages.count())+ ' messages')
        for msg in messages:
            self._mqtt_publish(msg)

    def _mqtt_send_lost_messages(self):
        # If client is connected, all messages stored in memory where sent, and there was messages lost
        # Update database sent status of messages
        if self._mqtt_connected and self._mqtt_messages_lost and not self._mqtt_client._out_messages:
            count = Message.update({Message.sent: True}).where(Message.sent == False).order_by(Message.timestamp.asc()).limit(self._mqtt_max_queue).execute()
            self._mqtt_messages_lost = False
            self.log_message(module = 'database:memory', msg = 'Sent '+ str(count)+ ' messages')
            gc.collect()

            # If there where messages not sent and stored in local database, resend them
            if count >= self._mqtt_max_queue:
                self._mqtt_resend_from_db()

    def _mqtt_publish(self, msg):
        # Publish the message to the server and store result in msg_info
        data = msg.to_json()
        msg_info = self._mqtt_client.publish(msg.topic.value, data, qos = self.mqtt_qos, retain = self._mqtt_retain)

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
        # Debug log for mqtt messages
        self.log_message(module = MQTT_TYPE_READING + ' - ' +mqtt_err, msg = data, level = logging.DEBUG ,send_mqtt = False)

        # Save the message in the local database
        msg.save()
        # return True or false
        return msg.sent

    def _create_topic(self, topic_type, t = ''):
        # Creates topic with format:
        # {id}/{topic_type}/{t}
        # BEFORE
        # final_value = self.uuid + '/' + topic_type
        final_value = topic_type
        if t:
            final_value += '/' + t
        if topic_type == MQTT_TYPE_MODULE and t != '#':
            final_value += '/fmt/txt'
        elif t != '#':
            final_value += '/fmt/json'
        # If topic was already in database the get if not create
        topic, _ = Topic.get_or_create(value = final_value)
        return topic

    @property
    def mqtt_publish_topic(self):
        return self._mqtt_publish_topic

    @mqtt_publish_topic.setter
    def mqtt_publish_topic(self, value):
        self._mqtt_publish_topic = self._create_topic(topic_type = MQTT_TYPE_READING)

    def _read_data(self):
        # Read line from serial and remove \n character
        if not self._serial:
            raise ValueError('Serial is not set!')

        data = self._serial.readline().rstrip().split('\t')

        timestamp = datetime.datetime.utcnow()

        keys = ["runtime","spoven","toven","spcoil","tcoil","spband","tband","spcat","tcat","tco2","pco2","co2","flow","curr","countdown","statusbyte"]

        dict_data = {}
        dict_data['timestamp'] = timestamp

        for i,key in enumerate(keys):
            if i == len(keys)-1:
                dict_data[key] = str(data[i])
            else:
                dict_data[key] = float(data[i])


        return dict_data

    def add_module(self, imodule):
        # Adds modules to instrument imodules and sets its serial
        if imodule.name in self._imodules.keys():
            msg = imodule.name + ' already exists! Modules cannot have the same name.'
            self.log_message(module = "Instrument", msg = msg, level = logging.CRITICAL, send_mqtt = False)
            raise ValueError(msg)

        imodule.serial = self._serial
        self._imodules[imodule.name] = imodule

    def get_module(self, name):
        # TODO
        # Try (*maybe)
        # Get module
        return self._imodules[name]

    def get_jobs(self):
        jobs = {'jobs':[]}
        for job in self.scheduler.get_jobs():
            id, args = job.args
            jobs['jobs'].append({'id':id, 'trigger': str(job.trigger), 'actions':args})
        json_jobs = json.dumps(jobs)
        topic = self._create_topic(topic_type = MQTT_TYPE_JOBS)
        msg_info = self._mqtt_client.publish(topic.value, json_jobs, qos = self.mqtt_qos, retain = self._mqtt_retain)
        return json_jobs

    def calculate_analysis(self, countdown):
        try:
            ppmtoug = 12.01/22.4
            co2 = []
            runtime = []
            t1 = Message.select().where(Message.sample == True and Message.countdown == int(countdown)).order_by(Message.timestamp.desc()).limit(1).get().timestamp
            t0 = t1 - datetime.timedelta(seconds = 5)
            t2 = t1 + datetime.timedelta(seconds = 630)
            baseline = Message.select(pw.fn.AVG(Message.co2).alias('avg')).where((Message.sample == True)&(Message.timestamp >= t0)&(Message.timestamp <= t1)).get().avg
            messages = Message.select().where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2))
            flowrate = messages.select(pw.fn.AVG(Message.flow).alias('avg')).where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2)).get().avg
            max_temp = messages.select(pw.fn.MAX(Message.toven).alias('max')).where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2)).get().max
            for m in messages:
                co2.append((m.co2 - baseline)*ppmtoug)
                runtime.append(m.runtime)
            deltatc = np.array(co2)*flowrate
            total_carbon = np.trapz(deltatc, x=np.array(runtime))
            timestamp = datetime.datetime.utcnow()
            message = Message(topic = self.mqtt_analysis_topic,timestamp = timestamp, total_carbon = total_carbon, max_temp = max_temp, baseline = baseline ,sample = False)
            self._mqtt_publish(message)
            self.log_message(module = 'analysis', msg = "Analysis successful: Carbon=" + str(total_carbon) + ' Temp=' + str(max_temp) + ' Baseline=' + str(baseline), level = logging.INFO)
            return message

        except Exception as e:
            self.log_message(module = 'analysis', msg = "Analysis not successful: " + str(e), level = logging.ERROR)


    def _run_actions(self, event_name, actions):
        # Runs a list of actions given in tuple form: (action_type, name, value)
        # Not logged becasue scheduler already logs jobs
        for action_type, name, value in actions:
            if action_type == 'mode':
                self.run_mode(name)
            elif action_type == 'module':
                self.run_action(name, value)
            elif action_type == 'wait':
                self.log_message(module = event_name, msg = "Waiting "+ value + " " + name)
                time.sleep(convert_to_seconds(name, int(value)))
            elif action_type == 'analyse':
                self.calculate_analysis(name)
            else:
                raise ValueError("Invalid action type: " + action_type)

    def run_mode(self, name):
        # Run mode actions
        module = "instrument"
        try:
            actions = self._modes[name]
            self.log_message(module = module, msg = "Started mode: " + name)
            self._run_actions(name, actions)
            self.log_message(module = module, msg = "Mode executed successfully: " + name)
        except Exception as e:
            self.log_message(module = module, msg = "Mode did not execute: " + name + str(e), level = logging.ERROR)

    def add_job(self, name = None, actions = None, **trigger_args):
        """
        Adds a job to scheduler with helper function to call SingletonInstrument._run_actions(actions)
        trigger options: 'cron' | 'interval' | 'date'
        name is the id and name of job that is going to be stored by the scheduler
        actions list and format  => [['action_type_1','name_1','value_1']... ['action_type_n','name_n','value_n']]
        trigger_args depend on type of trigger, see apscheduler documentation.
        ej. add_job('interval', 'example_name', [['module','example_module','action_1'], ['module','example_module','action_2']], minutes = 10 )
        """
        try:
            self.validate_actions(actions)
            # Because scheduler stores arguments in database, self is not serializable
            # Therefore we use helper function with actions calling on the singleton
            if trigger_args['trigger'] == 'cron':
                self.scheduler.add_job(helper_run_job, trigger_args['cron'], name=name , id=name, replace_existing=True, args = [name, actions], timezone = 'UTC')
            else:
                self.scheduler.add_job(helper_run_job, name=name , id=name, replace_existing=True, args = [name, actions], timezone = 'UTC', **trigger_args)
            status = "Job added: " + name +'-- Trigger:' + str(trigger_args)
            level = logging.INFO
        except Exception as e:
            status = str(e) + " Job not added: " + name
            level = logging.ERROR
        self.log_message(module = "instrument", msg = status, level = level)


    def validate_actions(self, actions):
        # Will test and raise error if not valid
        try:
            for action_type, module, action in actions:
                if action_type == 'mode':
                    self._modes[module]
                elif action_type == 'wait':
                    int(action)
                elif action_type == 'module':
                    values = action.split('=')
                    self._imodules[module].validate_action(values[0])
                else:
                    int(module)
                    if action_type != 'analyse':
                        raise
        except Exception as e:
            raise ValueError("Invalid actions!")


    def add_mode(self, name, actions):
        try:
            self.validate_actions(actions)
            self._modes[name] = actions
            status = "Mode saved successfully: "+ name
            level = logging.INFO
        except Exception as e:
            status = str(e) + " :: Mode not added: " + name
            level = logging.ERROR
        self.log_message(module = "instrument", msg = status, level = level)


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
        """
        Starts async MQTT client, sends lost messages when connected, starts scheduler and starts reading data
        """
        self.log_message(module = self.name, msg = self.uuid)
        self._mqtt_client.loop_start()
        self._mqtt_resend_from_db()
        self.scheduler.start()
        if not test:
            self.log_message(module = self.name, msg = "Starting reader on topic = "+ self.mqtt_publish_topic.value)
            self.start_reader()

    def _get_timestamp(self):
        # Return timestamp with user set format
        # return datetime.datetime.now().strftime(self.date_format)
        return datetime.datetime.utcnow().isoformat()

    def memory_usage(self):
        process = psutil.Process(os.getpid())
        mb = process.memory_info().rss/1000000
        self.log_message(module = 'memory', msg = str(mb)+ ' mb', level = logging.INFO)

    def start_reader(self):
        while(True):
            try:
                self._mqtt_send_lost_messages()
                data = self._read_data()
                data['topic'] = self.mqtt_publish_topic
                message = Message(**data)
                self._mqtt_publish(message)
            except KeyboardInterrupt:
                self.stop()
                break
            except serial.SerialException as se:
                self.log_message(module = "serial", msg = str(se), level = logging.WARN)
                self._serial.close()
                self._serial = self._set_up_serial()
                for name in self._imodules:
                    self._imodules[name].serial = self._serial

            except Exception as e:
                self.log_message(module = "reading", msg = str(e), level = logging.WARN)

    def stop(self):
        self._mqtt_client.loop_stop()
        self.log_message(module = 'mqttclient', msg = "stopped")
        self._serial.close()
        self.log_message(module = 'serial', msg = "closed")
        self.scheduler.shutdown()
