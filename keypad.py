from pad4pi import rpi_gpio
from RPi import GPIO
from time import sleep
import paho.mqtt.publish as publish


GPIO.setmode(GPIO.BCM)

GPIO.setup(25, GPIO.OUT)
GPIO.output(25, GPIO.LOW)


entered_passcode = ""

KEYPAD = [
    [1, 2, 3, "A"],
    [4, 5, 6, "B"],
    [7, 8, 9, "C"],
    ["*", 0, "#", "D"]
]

ROW_PINS = [17, 27, 23, 22] # BCM numbering
COL_PINS = [16, 20, 26, 21] # BCM numbering


def cleanup():
    global entered_passcode
    entered_passcode = ""
    
def digit_entered(key):
    global entered_passcode

    entered_passcode += str(key)
    print(entered_passcode)
    
    if len(entered_passcode) == 6:
        publish.single("otp", f"entered;{entered_passcode}")
        cleanup()
        sleep(1)

def non_digit_entered(key):
    global entered_passcode

    if key == "*" and len(entered_passcode) > 0:
        entered_passcode = entered_passcode[:-1]
        print(entered_passcode)

def key_pressed(key):
    GPIO.output(25, GPIO.HIGH)
    try:
        int_key = int(key)
        if int_key >= 0 and int_key <= 9:
            digit_entered(key)
    except ValueError:
        non_digit_entered(key)
    sleep(0.1)
    GPIO.output(25, GPIO.LOW)

try:
    factory = rpi_gpio.KeypadFactory()
    keypad = factory.create_keypad(keypad=KEYPAD,row_pins=ROW_PINS, col_pins=COL_PINS) # makes assumptions about keypad layout and GPIO pin numbers

    keypad.registerKeyPressHandler(key_pressed)

    print("Enter your passcode.")
    print("Press * to clear previous digit.")

    while True:
        sleep(1)
except KeyboardInterrupt:
    print("Goodbye")
finally:
    cleanup()