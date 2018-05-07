from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float, Datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import with_polymorphic
import datetime

engine = create_engine('sqlite:///local_store.db')
Base = declarative_base()
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

class Topic(Base):
    __tablename__ = 'topic'
    id = Column(Integer, primary_key=True)
    value = Column(String(250))
    messages = relationship('Message')


class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    timestamp = Column(Datetime, default=datetime.datetime.utcnow)
    sent = Column(Boolean)
    topic_id = Column(Integer, ForeignKey('topic.id'))
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
    cosa_nueva = Column(String(250))
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

session = DBSession()

new_analisis = Analysis(cosa_nueva='analisis', timestamp="1234")
new_sample = Sample(cosa_nueva_otra='sammple', timestamp="1234")
session.add(new_analisis)
session.add(new_sample)
session.commit()

eng_plus_manager = with_polymorphic(Message, [Analysis, Sample])

messages = session.query(eng_plus_manager).all()
for m in messages:
    m.to_json()
