import lib.SIM7000E as SIM7000E
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from time import sleep, time
from datetime import datetime
import config

allowed_numbers = config.sms.get('allowed_numbers')
notify_numbers = config.sms.get('notify_numbers')

sms = SIM7000E.modem()

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("sms")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    time_now = datetime.fromtimestamp(time())
    message = msg.payload.decode("UTF-8")
    print("Message:", message)
    for i in notify_numbers:
        sms.send(i, f"[LOG, {time_now}]: {message}")

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.connect("localhost", 1883, 60)

while True:
    mqttc.loop()
    sleep(2)
    sms_recv = sms.receive()
    print(sms_recv)
    for i in sms_recv:
        if i.get('number') in allowed_numbers:
            if len(i.get('content')) == 6 and str(i.get('content')).isdigit():
                mqttc.publish("otp", f"verify;{i.get('content')}")
            else:
                time_now = datetime.fromtimestamp(time())
                sms.send(i.get('number'), f"[LOG, {time_now}]: SMS content is incorrect")
        else:
            for j in notify_numbers:
                time_now = datetime.fromtimestamp(time())
                sms.send(j, f"[LOG, {time_now}]: Someone tried to open doors using unauthorized number: {i.get('number')}")
    sleep(5)