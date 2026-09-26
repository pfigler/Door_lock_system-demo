from RPi import GPIO
from mfrc522 import MFRC522
from time import sleep
import paho.mqtt.publish as publish
import config

allowed_tags = config.rfid.get('allowed_tags')
reader = MFRC522(pin_mode=11, pin_rst=5)

def uid_to_num(uid):
    n = 0
    for i in range(0, 5):
        n = n * 256 + uid[i]
    return n

def read_id_no_block():
    (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        return None
    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        return None
    return uid_to_num(uid)

def read_id():
    id = read_id_no_block()
    while not id:
      id = read_id_no_block()
    return id

while True:
        try:
                id = read_id()
                print("ID:", id)
                if id in allowed_tags:
                    publish.single("otp", "require;rfid")
                else:
                    publish.single("lcd", "3;Tag not allowed")
                    publish.single("sms", "Someone tried to gain unauthorized access to door using RFID tag.")
                sleep(2)
        finally:
                GPIO.cleanup()
                
