# Raspberry Pi Smart Door Lock Demo

A Raspberry Pi based electronic door lock prototype that combines keypad, RFID, SMS one time codes, and face recognition with relay based door control. This repository is the public demo version of an engineering thesis project.

## Purpose

The project demonstrates how several access inputs can be coordinated by independent Python processes on a Raspberry Pi. A local MQTT broker carries events between those processes, and the relay process drives the door lock and status outputs.

## Features

- Check entered keypad passcodes and generate a time limited prompt for a time based one time password (TOTP).
- Read RFID tags and request a TOTP step for configured tags.
- Receive SMS-based access requests through a serial modem and validate submitted codes using configured TOTP secrets.
- Detect an authorized face from the camera feed and request a TOTP step.
- Detect people in camera frames with a pretrained YOLOv5s model and record video around detected motion.
- Show status and prompts on an I2C character LCD and send event notifications by SMS.
- Drive the lock and two status outputs through Raspberry Pi GPIO.
- Serve a camera MJPEG live view over HTTP.

## Architecture

The main scripts run as separate processes and communicate using MQTT topics on `localhost:1883`:

```text
Keypad ----+
RFID ------+--> otp.py --> door / lcd / sms topics
Camera ----+       ^                  |
SMS modem ----------+                  +--> relay.py --> GPIO outputs / door lock
                                        +--> lcd.py ----> I2C LCD
                                        +--> sms.py ----> SIM7000E modem
```

`otp.py` handles TOTP checks and access requests. A valid SMS submitted code is checked and can open the door; an accepted keypad passcode, authorized RFID tag, or authorized face starts the TOTP prompt flow. `relay.py` listens for an `open` message and activates its configured output sequence for 15 seconds. The camera also provides its own HTTP stream and writes motion recordings to the `recordings` directories.

## Technologies

- Python 3
- MQTT messaging using Paho MQTT and a broker expected on the local machine at port 1883
- Raspberry Pi GPIO, Picamera2, and I2C hardware interfaces
- OpenCV, NumPy, `face_recognition`, and serialized face encodings
- PyOTP for TOTP generation and validation
- PyTorch and the pretrained YOLOv5s model loaded through `torch.hub`
- FFmpeg command-line processing through the `ffmpeg` Python package
- PySerial and modem AT commands for SMS

The repository does not include a Python dependency manifest or pinned package versions. The list above reflects imports and runtime calls in the project source; it is not a tested installation recipe.

## Hardware referenced by the code

The code expects a Raspberry Pi with a compatible camera, an MFRC522 RFID reader, a GPIO keypad, an I2C character LCD, a SIM7000E serial modem, and a relay/door lock circuit. `lib/I2C_LCD.py` selects I2C bus 1 and address `0x27`. The keypad and relay scripts define GPIO pin assignments in source. The modem code uses `/dev/ttyS0` at 9600 baud. Check the source and your wiring before connecting hardware; the repository does not provide a complete wiring diagram.

## Authentication and security

The code supports configured keypad passcodes, RFID tag allowlisting, face matching against the loaded encodings, and TOTP checks. SMS authorization is based on configured allowed sender numbers, and configured notification numbers receive event messages.

This is a demonstration implementation, not a hardened access control product. MQTT connects to the local broker without application-level authentication or transport encryption configured in these scripts. The camera HTTP stream has no authentication and binds to all network interfaces on port `7123`. The code contains fixed access timing and camera authorization values in addition to values in the configuration template. Protect the device and its network, restrict access to the stream and broker, and review the access logic before any deployment. Face matching and TOTP behavior have not been independently security-audited.

## Project files

| File or directory | Purpose |
| --- | --- |
| `start.sh` | Starts the camera, keypad, RFID, SMS, OTP, LCD, and relay scripts. It assumes a particular virtual environment location and an X display setting. |
| `stop.sh` | Stops Python processes selected by its process-list pipeline; use with care because it is not scoped to this project. |
| `camera.py` | Camera stream, face-triggered access request, human detection, and motion recording. |
| `image_capture.py` | Captures face dataset images using the Pi camera. |
| `model_training.py` | Builds and saves face encodings from images under `dataset/`. |
| `facial_recognition.py` | Standalone face recognition preview utility. |
| `keypad.py`, `rfid.py` | Keypad and RFID input processes. |
| `otp.py` | MQTT access-flow coordinator and TOTP validation. |
| `sms.py` | SMS reception, code forwarding, and notifications. |
| `relay.py` | Door lock and status GPIO output control. |
| `lcd.py` | MQTT-driven LCD display control. |
| `lib/SIM7000E.py` | Serial modem SMS helper. |
| `lib/I2C_LCD.py` | I2C LCD driver. |
| `config.example.py` | Public template showing configuration keys and placeholder values. |
| `dataset/`, `encodings.pickle`, `recordings/` | Local/private data locations used for face images, serialized face encodings, and video recordings. These are not included in this public repository; face data and encodings should be treated as sensitive biometric information. |

## Configuration

The scripts that read runtime configuration import a module named `config`. `config.example.py` documents the expected dictionaries and keys:

- `sms`: `allowed_numbers` and `notify_numbers`
- `keypad`: `passcodes`
- `otp`: `tokens` and `timeout` (seconds)
- `rfid`: `allowed_tags`
- `door`: `open_time`
- `camera`: `allowed_faces` and `remote_port`
- `lcd`: `default_message`

Use the example file as a template for a private local `config.py` and replace placeholders with values appropriate to your test setup. Keep real credentials, phone numbers, RFID identifiers, face images/encodings, and private configuration out of the public repository. Some settings declared by the template are not read by the current implementation; for example, the camera stream port and authorized face name are set directly in `camera.py`, and relay timing is set directly in `relay.py`.

## Setup and running

The source verifies the following runtime assumptions, but the repository does not include an end-to-end installation script or dependency lockfile:

1. Use a Raspberry Pi environment with the required camera, GPIO, I2C, serial, and attached access-control hardware available.
2. Install Python packages and system components needed by the imports and external interfaces listed above. The scripts require an MQTT broker reachable at `localhost:1883`; broker installation and configuration are not included.
3. Provide a private `config.py` based on `config.example.py` and a compatible `encodings.pickle` generated by `model_training.py` from your own dataset.
4. Ensure the recording subdirectories referenced by `camera.py` exist and are writable.
5. Review `start.sh` for its fixed virtual-environment path and display setting, then adapt the environment locally if needed. From the repository directory, the provided launcher is `bash start.sh`. It starts the component scripts in the background and leaves `relay.py` in the foreground.

The utilities can also be run individually with Python 3 from the repository directory, subject to their hardware, configuration, broker, model, and data-file requirements. `image_capture.py` and `model_training.py` are preparation utilities rather than part of the launcher sequence.

## Demo and privacy note

This is the public demo version of an engineering thesis project. Real credentials, biometric data, and private configuration are intentionally excluded from the configuration template. Treat any locally generated face dataset and encoding file as sensitive biometric information, and do not publish those files or real access credentials.
