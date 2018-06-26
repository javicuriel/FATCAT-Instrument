*Application developed in **Python** to work in conjunction with any **MQTT broker** and any **Serial** controlled device.*

The application has one main class called **Instrument** which has as attributes multiple classes with the following structure:

* Instrument
  * MQTT Client
  * Serial
  * Scheduler
  * Logger
  * IModule *(Can have multiple)*




### **Installation**
1. Clone repository:
```
$ git clone https://github.com/javicuriel/GAW-Instrument
```
2. Travel to cloned folder:
```
$ cd GAW-Instrument
```
3. Open config.ini and check **[configuration file](#configuration-file)**.
4. Run installation script as sudo with serial connected:
```
$ sudo python installer.py
```

### **Configuration-file**
1. Set MQTT settings like the following example:
```ini
[MQTT_SETTINGS]
MQTT_ORG: 'kbld7d'
MQTT_SERVER: 'messaging.internetofthings.ibmcloud.com'
MQTT_PORT: 8883
MQTT_QOS: 1
MQTT_KEEPALIVE: 5
```
2. Set serial settings like the following example (Application will look for serial with **SERIAL_PORT_DESCRIPTION**):
```ini
[SERIAL_SETTINGS]
SERIAL_PORT_DESCRIPTION: 'NANOTDMRA'
SERIAL_BAUDRATE: 115200
SERIAL_PARITY: serial.PARITY_NONE
SERIAL_STOPBITS: serial.STOPBITS_ONE
SERIAL_BYTESIZE: serial.EIGHTBITS
SERIAL_TIMEOUT: 1
```
3. Set modules and their respective actions with the following format:
```ini
module_name:  'action:serial_action'...,'action_2:serial_action(range)'
```
ej.
```ini
[MODULES]
pump:  'on:U1000','off:U0000','flow:F0000-F0020'
band:  'on:B1000','off:B0000','temperature:S2000-S2100', 'p_parameters:P2000-P2100'
oven:  'on:O1000','off:O0000', 'burn_cycle_time:A0000-A0080', 'temperature:S1000-S1100'
valve: 'on:V1000','off:V0000'
licor: 'on:L1000','off:L0000'
extp:  'on:E1000','off:E0000'
```
4. Set modes and their respective actions with the following format:
```ini
mode_name: 'action_type_1:module_name_1:action_1'..., 'action_type_n:module_name_n:action_n'
```
ej.
```ini
[MODES]
analysis: 'module:licor:on', 'module:extp:off', 'module:valve:on', 'module:pump:on'
sampling: 'module:pump:off', 'module:valve:off', 'module:extp:on', 'module:licor:off'
```
