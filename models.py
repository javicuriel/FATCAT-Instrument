from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import with_polymorphic
import datetime, json

engine = create_engine('sqlite:///local_store.db',connect_args={'check_same_thread':False})
Base = declarative_base()

class Topic(Base):
    __tablename__ = 'topic'
    id = Column(Integer, primary_key=True)
    value = Column(String(250))
    messages = relationship('Message', back_populates="topic")


class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    sent = Column(Boolean, unique=False, default=True)
    topic_id = Column(Integer, ForeignKey('topic.id'))
    topic = relationship("Topic", back_populates="messages")
    __mapper_args__ = {
        'polymorphic_identity':'message',
        'polymorphic_on':type
    }
    def to_json(self):
        omit = {'id','sent','topic','_sa_instance_state'}
        data = {x: self.__dict__[x] for x in self.__dict__ if x not in omit}
        data['timestamp'] = data['timestamp'].isoformat()
        json_data = json.dumps(data)
        return json_data


class Analysis(Message):
    __tablename__ = 'analysis'
    id = Column(Integer, ForeignKey('message.id') ,primary_key=True)
    total_carbon = Column(Float)
    max_temp = Column(Float)
    __mapper_args__ = {
        'polymorphic_identity':'analysis',
    }


class Sample(Message):
    __tablename__ = 'sample'
    id = Column(Integer, ForeignKey('message.id') ,primary_key=True)
    runtime = Column(Float)
    spoven = Column(Float)
    toven = Column(Float)
    spcoil = Column(Float)
    tcoil = Column(Float)
    spband = Column(Float)
    tband = Column(Float)
    spcat = Column(Float)
    tcat = Column(Float)
    tco2 = Column(Float)
    pco2 = Column(Float)
    co2 = Column(Float)
    flow = Column(Float)
    curr = Column(Float)
    countdown = Column(Float)
    statusbyte = Column(Float)
    __mapper_args__ = {
        'polymorphic_identity':'sample'
    }

Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
poly = with_polymorphic(Message, [Analysis, Sample])



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


    def _get_action(self, message):
        # Action format: 'example' or 'example=67'
        commands = message.split('=')
        if len(commands) == 2:
            return commands[0], commands[1]
        elif len(commands) == 1:
            return commands[0], None
        else:
            raise ValueError("Command format is invalid:" + message)

    def set_value(self, actions, value):
        a, b = actions
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

    def run_action(self, message):
        if not self.serial:
            raise ValueError('Serial is not set!')

        action, value = self._get_action(message)

        if action in self.actions:
            try:
                if value:
                    serial_action = self.actions[action](value = value)
                    self.serial.write(serial_action)
                    return serial_action
                else:
                    serial_action = self.actions[action]
                    self.serial.write(serial_action)
                    return serial_action
            except:
                raise
        raise ValueError("Command not found:" + action)


    def __eq__(self, other):
        return self.name == other.name
