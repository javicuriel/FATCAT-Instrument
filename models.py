# Created by Javier Curiel
# Copyright (c) 2018 Javier Curiel. All rights reserved.

import peewee as pw
import datetime

db = pw.SqliteDatabase('local_store.db')

# Base model implemented for use of the same database for all models
class BaseModel(pw.Model):
    class Meta:
        database = db

class Topic(BaseModel):
    value = pw.CharField()

class Message(BaseModel):
    topic = pw.ForeignKeyField(Topic)
    payload = pw.CharField()
    sent = pw.BooleanField(default = False)
    timestamp = pw.DateTimeField(default=datetime.datetime.now)



class IModule(object):
    def __init__(self, name, is_reader = False):
        super(IModule, self).__init__()
        self.name = name
        self.serial = None
        self.actions = {}


    def set_action(self, action_name, serial_action):
        # When setting a user function, the return value must be in string format
        # setattr(self, action_name, serial_action)
        self.actions[action_name] = serial_action

    def set_actions(self, actions):
        self.actions = actions
        return self

    def _get_action(self, message):
        # Action format: 'example' or 'example=67'
        commands = message.split('=')
        if len(commands) == 2:
            return commands[0], commands[1]
        elif len(commands) == 1:
            return commands[0], None
        else:
            raise ValueError("Module:"+self.name +" Command format is invalid:" + message)


    def run_action(self, message):
        if not self.serial:
            raise ValueError('Serial is not set for Module:'+ self.name +'!')

        action, value = self._get_action(message)

        if action in self.actions:
            try:
                if value:
                    self.serial.write(self.actions[action](value))
                else:
                    self.serial.write(self.actions[action])
                return True
            except:
                raise
        raise ValueError("Module:"+self.name +" Command not found:" + action)


    def __eq__(self, other):
        return self.name == other.name
