#!/bin/bash

source /home/gocha/Door_lock_system/.venv/bin/activate
export DISPLAY=:0.0

python3 camera.py &
python3 keypad.py &
python3 rfid.py &
python3 sms.py &

python3 otp.py &

python3 lcd.py &
python3 relay.py