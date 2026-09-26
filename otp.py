import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import pyotp
import config
import _thread as thread
from time import sleep

tokens = config.otp.get('tokens')
timeout_otp = config.otp.get('timeout')
passcodes = config.keypad.get('passcodes')

is_otp = False
last_request = str()

def get_valid_codes():
    valid_codes = list()
    for i in tokens:
        j = pyotp.TOTP(i)
        valid_codes.append(j.now())
    return valid_codes

def verify_otp(code):
    valid_codes = get_valid_codes()
    if code in valid_codes:
        return True
    else:
        return False
    
def require_otp():
    global is_otp
    if not is_otp:
        thread.start_new_thread(otp_timeout, ())
    
def otp_timeout():
    global is_otp
    is_otp = True
    mqttc.publish("lcd", "0;Enter OTP")
    sleep(timeout_otp)
    mqttc.publish("lcd", "-1;default")
    is_otp = False
    
def send_sms():
    global last_request
    if last_request == 'sms':
        mqttc.publish("sms", "Door opened using SMS code")
    elif last_request == 'keypad':
        mqttc.publish("sms", "Door opened using keypad")
    elif last_request == 'face':
        mqttc.publish("sms", "Door opened using face recognition")
    elif last_request == 'rfid':
        mqttc.publish("sms", "Door opened using RFID tag")
    else:
        print('Request source not identified')
    last_request = ''
    
def parse_message(message):
    global last_request, is_otp
    
    # verify;otp - check against configured tokens with provided tolerancy
    # endered;passcode - check against pin or tokens
    # require;source - negates variable for x seconds
    command, data = message.split(';')
    
    match command:
        case 'verify':
            valid = verify_otp(data)
            if valid:
                mqttc.publish("door", "open")
                mqttc.publish("lcd", "15;Door open")
                last_request = 'sms'
                send_sms()
        case 'require':
            require_otp()
            last_request = data
        case 'entered':
            if is_otp:
                valid = verify_otp(data)
                if valid:
                    mqttc.publish("door", "open")
                    mqttc.publish("lcd", "15;Door open")
                    send_sms()
                elif not valid:
                    mqttc.publish("sms", "Someone provided invalid OTP")
            elif not is_otp:
                if data in passcodes:
                    require_otp()
                    last_request = 'keypad'
                elif data not in passcodes:
                    mqttc.publish("lcd", "3;PIN is incorrect")
        case _:
            print('Command not found')


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("otp")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    message = msg.payload.decode("UTF-8")
    print("Message:", message)
    parse_message(message)

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect #specify which function to run after connecting to server
mqttc.on_message = on_message #specify which function to run when receive message in topic
mqttc.connect("localhost", 1883, 60) #connecting client with server

while True:
    mqttc.loop()