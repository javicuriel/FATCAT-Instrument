import paho.mqtt.client as mqtt
import ssl
import jwt
from Instrument import *

def mqtt_on_connect(*args, **kwargs):
    print("Entro")

def mqtt_on_disconnect(*args, **kwargs):
    print("Salio")


def setup_mqtt_client():
    # Creates MQTT client
    client = mqtt.Client(
        client_id = 'projects/api-project-516409951425/locations/europe-west1/registries/instruments/devices/macbook-154505275890450',
        protocol= mqtt.MQTTv311,
        clean_session = False
    )
    # Connection settings
    client.connect_async(
        host = 'mqtt.googleapis.com',
        port = 8883
        # keepalive = self.mqtt_keep_alive
    )

    password = create_jwt('api-project-516409951425', 'rsa_private.pem', 'RS256')

    client.username_pw_set(
            username='unused',
            password=password
    )

    # Enable SSL/TLS support.
    client.tls_set(ca_certs='roots.pem', tls_version=ssl.PROTOCOL_TLSv1_2)

    # Sets callback functions for message arrival
    client.on_connect = mqtt_on_connect
    client.on_disconnect = mqtt_on_disconnect


    return client

client = setup_mqtt_client()
client.loop_start()
while True:
    pass
