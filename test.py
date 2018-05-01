from Models import *
import datetime
import numpy as np

ppmtoug = 12.01/22.4
t1 = Message.select().where(Message.countdown == 70).order_by(Message.timestamp.desc()).limit(1).get().timestamp
t0 = t1 - datetime.timedelta(seconds = 5)
t2 = t1 + datetime.timedelta(seconds = 630)
baseline = Message.select(pw.fn.AVG(Message.co2).alias('avg')).where(Message.timestamp >= t0 and Message.timestamp <= t1).get().avg
messages = Message.select(Message.co2, Message.flow, Message.runtime).where(Message.timestamp >= t1 and Message.timestamp <= t2)
flowrate = messages.select(pw.fn.AVG(Message.flow).alias('avg')).get().avg
co2 = []
runtime = []
for m in messages:
    co2.append((m.co2 - baseline)*ppmtoug)
    runtime.append(m.runtime)

deltatc = np.array(co2)*flowrate
total_carbon = np.trapz(deltatc, x=np.array(runtime))
print(total_carbon)
