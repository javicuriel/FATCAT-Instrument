import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client(
    client_id = 'd:{}:{}:{}'.format('brd98r', 'instrument', '11'),
    protocol= mqtt.MQTTv311,
    clean_session = False
)

client.username_pw_set(
        username='use-token-auth',
        password= '@pQz-B4nq2mdbGQ5--'
)

# Connection settings
client.connect_async(
    host = 'brd98r.messaging.internetofthings.ibmcloud.com',
    port = 8883,
    keepalive = 5
)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

def on_disconnect(client, userdata, flags, rc):
    print("Disconnected with result code "+str(rc))


client.on_connect = on_connect;
client.on_disconnect = on_disconnect;
client.tls_set(cert_reqs = ssl.CERT_REQUIRED, tls_version = ssl.PROTOCOL_TLSv1_2)
client.loop_start()

while True:
    pass
