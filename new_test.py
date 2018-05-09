import peewee as pw
from Models import *
import numpy as np

ppmtoug = 12.01/22.4
co2 = []
runtime = []
t1 = Message.select().where(Message.sample == True and Message.countdown == 70).order_by(Message.timestamp.desc()).limit(1).get().timestamp
t0 = t1 - datetime.timedelta(seconds = 5)
t2 = t1 + datetime.timedelta(seconds = 630)
baseline = Message.select(pw.fn.AVG(Message.co2).alias('avg')).where((Message.sample == True)&(Message.timestamp >= t0)&(Message.timestamp <= t1)).get().avg
messages = Message.select().where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2))
flowrate = messages.select(pw.fn.AVG(Message.flow).alias('avg')).where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2)).get().avg
max_temp = messages.select(pw.fn.MAX(Message.toven).alias('max')).where((Message.sample == True)&(Message.timestamp >= t1)&(Message.timestamp <= t2)).get().max
for m in messages:
    print(m.__dict__)
    co2.append((m.co2 - baseline)*ppmtoug)
    runtime.append(m.runtime)
deltatc = np.array(co2)*flowrate
total_carbon = np.trapz(deltatc, x=np.array(runtime))
timestamp = datetime.datetime.utcnow()
# message = Message(topic = "self.mqtt_analysis_topic",timestamp = timestamp, total_carbon = total_carbon, max_temp = max_temp, sample = False)
