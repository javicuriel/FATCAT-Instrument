from Models import Topic
from Models import Sample
from Models import Message
from Models import Analysis
from Models import IModule
from Models import DBSession
from Models import poly
import datetime
from sqlalchemy.sql import func
import numpy as np

session = DBSession()

ppmtoug = 12.01/22.4
co2 = []
runtime = []
t1 = self.session.query(Sample).filter(Sample.countdown == 0).order_by(Sample.timestamp.desc()).first().timestamp
t0 = t1 - datetime.timedelta(seconds = 5)
t2 = t1 + datetime.timedelta(seconds = 630)
baseline = self.session.query(func.avg(Sample.co2).label('avg')).filter(Sample.timestamp >= t0).filter(Sample.timestamp <= t1).one().avg
samples = self.session.query(Sample.co2, Sample.runtime).filter(Sample.timestamp >= t1).filter(Sample.timestamp <= t2).all()
flowrate = self.session.query(func.avg(Sample.flow).label('avg')).filter(Sample.timestamp >= t1).filter(Sample.timestamp <= t2).one().avg
max_temp = self.session.query(func.max(Sample.toven).label('max')).filter(Sample.timestamp >= t1).filter(Sample.timestamp <= t2).one().max
for s in samples:
    co2.append((s.co2 - baseline)*ppmtoug)
    runtime.append(s.runtime)
deltatc = np.array(co2)*flowrate
total_carbon = np.trapz(deltatc, x=np.array(runtime))
timestamp = datetime.datetime.utcnow()
message = Analysis(timestamp = timestamp, total_carbon = total_carbon, max_temp = max_temp)
self._mqtt_publish(message)
