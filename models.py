# from peewee import *
import peewee as pw
import logging

db = pw.SqliteDatabase('local_store.db')

# Base model implemented for use of the same database for all models
class BaseModel(pw.Model):
    class Meta:
        database = db

class Message(BaseModel):
    topic = pw.CharField()
    payload = pw.CharField()
    sent = pw.BooleanField(default = False)

    class Meta:
        database = db

class IModule(object):
    def __init__(self, name):
        super(IModule, self).__init__()
        self.name = name
        self.serial = None

    def set_action(self, action_name, serial_action):
        # When setting a user function, the return value must be in string format
        setattr(self, action_name, serial_action)

    # TODO
    # Not working
    def set_actions(self, actions):
        map(self.set_action, actions)

    def run_action(self, action):
        if not self.serial:
            e = 'Serial is not set for Module:'+ self.name +'!'
            logging.critical(e)
            raise ValueError(e)

        # Action format: 'on' or 'example=67'
        commands = action.split('=')
        e = "Module:"+self.name +" Command not found:" + action
        not_found = ValueError(e)
        try:
            if hasattr(self, commands[0]):
                if len(commands) == 2:
                    value = int(commands[1])
                    self.serial.write(getattr(self, commands[0])(value))
                    # logging.info("Wrote serial command:"+ commands[0] + '=' + commands[1])
                elif len(commands) == 1:
                    self.serial.write(getattr(self, action))
                    # logging.info("Wrote serial command:"+ commands[0] )
                else:
                    raise not_found
                return True
            else:
                raise not_found
        except Exception as e:
            # if e == not_found:
                # logging.error(action + ' not found for module '+ self.name + '!')
            return False

    def __eq__(self, other):
        return self.name == other.name
