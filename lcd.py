import lib.I2C_LCD as I2C_LCD
from time import *
import paho.mqtt.client as mqtt
import config

mylcd = I2C_LCD.lcd()
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
default_message = config.lcd.get('default_message')


def dsp_simple(message):
    mylcd.lcd_clear()
    mylcd.lcd_display_string(message[:16], 1)
    mylcd.lcd_display_string(message[16:], 2)
    
def dsp_newline(message):
    text = message.split('\n')
    mylcd.lcd_clear()
    mylcd.lcd_display_string(text[0], 1)
    mylcd.lcd_display_string(text[1], 2)
    
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("lcd")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global default_message
    
    message = msg.payload.decode("UTF-8")
    print("Message:", message)
    
    timeout, data = message.split(';')
    timeout = int(timeout)
    
    if timeout == 0:
        dsp_simple(data)
    if timeout > 0:
        dsp_simple(data)
        sleep(timeout)
        dsp_newline(default_message)
    if timeout == -1:
        dsp_newline(default_message)
    

dsp_newline(default_message)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.connect("localhost", 1883, 60)

while True:
    mqttc.loop()