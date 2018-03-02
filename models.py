# from peewee import *
import peewee as pw

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
            raise ValueError('Serial is not set!')

        # Action format: 'on' or 'example=67'
        commands = action.split('=')
        not_found = ValueError("Command not found: " + action)
        try:
            if hasattr(self, commands[0]):
                if len(commands) == 2:
                    value = int(commands[1])
                    # print("Recieved command: "+ commands[0] + ' ' + commands[1])
                    self.serial.write(getattr(self, commands[0])(value))
                elif len(commands) == 1:
                    # print("Recieved command: "+ commands[0] )
                    self.serial.write(getattr(self, action))
                else:
                    raise not_found

                return True

            else:
                raise not_found
        except Exception as e:
            return False

    def __eq__(self, other):
        return self.name == other.name
