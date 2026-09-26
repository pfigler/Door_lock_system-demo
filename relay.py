from RPi import GPIO
from time import sleep
import paho.mqtt.client as mqtt

GPIO.setmode(GPIO.BCM)

# Pin 13: Door lock, status GREEN
GPIO.setup(13, GPIO.OUT)
GPIO.output(13, GPIO.LOW)

# Pin 24: Status RED
GPIO.setup(24, GPIO.OUT)
GPIO.output(24, GPIO.HIGH)

door_open = False

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("door")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global door_open
    
    message = msg.payload.decode("UTF-8")
    print("Message:", message)
    if message == "open" and not door_open:
        door_open = True
        GPIO.output(13, GPIO.LOW)
        GPIO.output(24, GPIO.HIGH)
        sleep(0.1)
        GPIO.output(13, GPIO.HIGH)
        GPIO.output(24, GPIO.LOW)
        sleep(15)
        GPIO.output(13, GPIO.LOW)
        GPIO.output(24, GPIO.HIGH)
        door_open = False
        mqttc.publish("sms", 'Door closed after 15 seconds.')
    
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect #specify which function to run after connecting to server
mqttc.on_message = on_message #specify which function to run when receive message in topic
mqttc.connect("localhost", 1883, 60) #connecting client with server

while True:
    mqttc.loop()