import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import with_polymorphic

Base = declarative_base()

class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    timestamp = Column(String(250))
    sent = Column(Boolean)
    topic = Column(String(250))
    __mapper_args__ = {
        'polymorphic_identity':'message',
        'polymorphic_on':type
    }
    def to_json(self):
        omit = {'id','sent','topic','_sa_instance_state'}
        data = {x: self.__dict__[x] for x in self.__dict__ if x not in omit}
        print(data)


class Analysis(Message):
    __tablename__ = 'analysis'
    id = Column(Integer, ForeignKey('message.id') ,primary_key=True)
    cosa_nueva = Column(String(250))
    __mapper_args__ = {
        'polymorphic_identity':'analysis',
    }


class Sample(Message):
    __tablename__ = 'sample'
    id = Column(Integer, ForeignKey('message.id') ,primary_key=True)
    cosa_nueva_otra = Column(String(250))
    __mapper_args__ = {
        'polymorphic_identity':'sample'
    }
engine = create_engine('sqlite:///sqlalchemy_example.db')
Base.metadata.create_all(engine)

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
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
