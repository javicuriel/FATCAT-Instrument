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
    def __init__(self, name, port):
        super(IModule, self).__init__()
        self.name = name
        self.port = port

    def set_action(self, action_name, serial_action):
        setattr(self, action_name, serial_action)

    def set_actions(self, actions):
        map(set_action, actions)

    def run_action(self, action):
        commands = action.split('=')
        not_found = ValueError("Command not found: " + action)
        try:
            if hasattr(self, commands[0]):
                if len(commands) == 2:
                    value = int(commands[1])
                    print("Recieved command: "+ commands[0] + ' ' + commands[1])
                    print(getattr(self, commands[0])(value))
                    # self.port.write(getattr(self, commands[0])(value))
                elif len(commands) == 1:
                    print("Recieved command: "+ commands[0])
                    print(getattr(self, action))
                    # self.port.write(getattr(self, action))
                else:
                    raise not_found

                return True

            else:
                raise not_found
        except Exception as e:
            return False

    def __eq__(self, other):
        return self.name == other.name
