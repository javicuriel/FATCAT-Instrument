# Created by Javier Curiel
# Copyright (c) 2018 Javier Curiel. All rights reserved.

import peewee as pw
import datetime
import json

# db = pw.SqliteDatabase(storage_location+'/local_store.db')
db = pw.SqliteDatabase(None)

# Base model implemented for use of the same database for all models
class BaseModel(pw.Model):
    class Meta:
        database = db

class Topic(BaseModel):
    value = pw.CharField()


class Message(BaseModel):
    sent = pw.BooleanField(default = False)
    timestamp = pw.DateTimeField(default=datetime.datetime.now)

    sample = pw.BooleanField(default = True)
    runtime = pw.FloatField(null = True)

    spoven = pw.FloatField(null = True)
    toven = pw.FloatField(null = True)
    spcoil = pw.FloatField(null = True)
    tcoil = pw.FloatField(null = True)
    spband = pw.FloatField(null = True)
    tband = pw.FloatField(null = True)
    spcat = pw.FloatField(null = True)
    tcat = pw.FloatField(null = True)
    tco2 = pw.FloatField(null = True)
    pco2 = pw.FloatField(null = True)
    co2 = pw.FloatField(null = True)
    flow = pw.FloatField(null = True)
    curr = pw.FloatField(null = True)
    countdown = pw.FloatField(null = True)
    statusbyte = pw.CharField(null = True)

    timezone = pw.FloatField(null = True)


    def to_json(self):
        omit = {'id','sent','sample'}
        data = {x: self.__data__[x] for x in self.__data__ if x not in omit and self.__data__[x] != None}
        data['timestamp'] = data['timestamp'].isoformat() + 'Z'
        json_data = json.dumps(data)
        return json_data


class IModule(object):
    def __init__(self, name, is_reader = False):
        super(IModule, self).__init__()
        self.name = name
        self.serial = None
        self.actions = {}


    def set_action(self, action_name, serial_action):
        # When setting a user function, the return value must be in string format
        # setattr(self, action_name, serial_action)
        self.actions[action_name] = self._get_serial_action(serial_action)

    def set_actions(self, actions):
        self.actions = actions

    def validate_action(self, action):
        # TODO
        # Check is value is valid within range
        if action in self.actions:
            return True
        else:
            raise ValueError("Invalid action: "+ action)


    def _format_action(self, action):
        # Action format: 'example' or 'example=67'
        commands = action.split('=')
        if len(commands) == 2:
            return commands[0], commands[1]
        elif len(commands) == 1:
            return commands[0], None
        else:
            raise ValueError("Command format is invalid:" + action)

    def set_value(self, range, value):
        a, b = range
        serial_action = range_a = range_b = ''
        for i, char in enumerate(a):
            if a[i] != b[i]:
                serial_action = a[:i]
                range_a = a[i:]
                range_b = b[i:]
                break
        if int(value) >= int(range_a) and int(value) <= int(range_b):
            extra_zeros = len(a) - len(serial_action + value)
            serial_action += '0' * extra_zeros
            serial_action += value
            return serial_action
        raise ValueError("Value is out of range: " + value)

    def _check_range(self, serial_action):
        a, b = serial_action
        return a < b and len(a) == len(b) and a != b


    def _get_serial_action(self, serial_action_string):
        serial_action = serial_action_string.split('-')
        e = ValueError("Module:"+self.name +" serial action format is invalid:" + serial_action_string)
        if len(serial_action) == 2:
            if not self._check_range(serial_action):
                raise e
            return lambda value: self.set_value(serial_action, value = value)
        elif len(serial_action) == 1:
            return serial_action[0]
        else:
            raise e

    def run_action(self, action_name):
        if not self.serial:
            raise ValueError('Serial is not set!')

        action, value = self._format_action(action_name)

        if action in self.actions:
            try:
                if value:
                    serial_action = self.actions[action](value = value)
                else:
                    serial_action = self.actions[action]

                self.serial.write(serial_action.encode())
                return serial_action
            except:
                raise
        raise ValueError("Command not found:" + action)


    def __eq__(self, other):
        return self.name == other.name

class OvenLog(pw.Model):
    timestamp = pw.DateTimeField(default=datetime.datetime.now)
    class Meta:
        database = pw.SqliteDatabase(None)

def init_models(storage_location):
    # Create DB tables if not exists
    BaseModel._meta.database.init(storage_location+'/local_store.db')
    OvenLog._meta.database.init(storage_location+'/oven_log.db')

    Topic.create_table(True)
    Message.create_table(True)

    OvenLog.create_table(True)
