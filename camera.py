#################################################################
#                            Common                             #
#################################################################

import time
import cv2
import numpy as np

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput

framerate = 15

#################################################################
#                        Face recognition                       #
#################################################################

import face_recognition
import pickle
import paho.mqtt.publish as publish


# Load pre-trained face encodings
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]

# Initialize our variables
cv_scaler = 4 # this has to be a whole number

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

# List of names that will trigger the GPIO pin
authorized_names = ["EXAMPLE_USER"] # Replace with names you wish to authorise THIS IS CASE-SENSITIVE


def process_frame(frame):
    global face_locations, face_encodings, face_names

    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    
    # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    
    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')
    
    face_names = []
    authorized_face_detected = False
    
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        
        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
            # Check if the detected face is in our authorized list
            if name in authorized_names:
                authorized_face_detected = True
        face_names.append(name)
    
    # Control based on face detection
    if authorized_face_detected:
        publish.single("otp", "require;face")
        print("Face recognized")
        time.sleep(10)
    
    return frame


#################################################################
#                           Live view                           #
#################################################################

import io
import logging
import socketserver
from http import server
from threading import Condition
import _thread as thread

PAGE = """\
<html>
<head>
<title>picamera2 MJPEG streaming</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming</h1>
<img src="stream.mjpg" width="800" height="400" />
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    
def serverStart():
    try:
        address = ('', 7123)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        picam2.stop_recording()
    

#################################################################
#                        Motion Detector                        #
#################################################################

import ffmpeg
import torch


lsize = (800, 400)
w, h = lsize
encoding = False
ltime = 0
rtime = 10.0
ttime = 0.0

# Define buffer and its size
buffer_time = 10
buffer_size = framerate * buffer_time
buffer = list()

# Load model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)


def video_magic(name: float):
    global framerate
    ffmpeg.input(f"recordings/temp/{int(name)}_before.mp4").output(f"recordings/base/{int(name)}_before.mp4", r=framerate, vcodec='libx264', acodec='aac', map='0').run()
    print("Recorded buffer was successfully reencoded to MP4")
    
    ffmpeg.input(f"recordings/temp/{int(name)}_after.h264", framerate=15).output(f"recordings/temp/{int(name)}_after.mp4", r=framerate, vcodec='copy', acodec='copy', map='0').run()
    ffmpeg.input(f"recordings/temp/{int(name)}_after.mp4").output(f"recordings/base/{int(name)}_after.mp4", r=framerate, vcodec='libx264', acodec='aac', map='0').run()
    print("Recording was successfully converted to MP4")
    
    with open(f"recordings/base/{int(name)}.txt", 'w') as f:
        f.write(f"file '{int(name)}_before.mp4'\n")
        f.write(f"file '{int(name)}_after.mp4'\n")
    time.sleep(0.1)
    ffmpeg.input(f"recordings/base/{int(name)}.txt", format='concat', safe=0).output(f"recordings/{int(name)}.mp4", c='copy').run()
    print("Recordings merged successfully")


def detect_human(frame):
    global model, buffer, buffer_size, ltime, rtime, ttime, encoding

    buffer.append(frame)
    
    # Perform inference
    results = model(frame) # Model YOLOv5s zwraca obiekty wykryte w przekazanej klatce

    # Filter detections to only humans (class 0 corresponds to humans in YOLOv5)
    human_detections = results.xywh[0][results.xywh[0][:, -1] == 0] # Filtrowanie rezultatów pod kątem człowieków; 0 to nie ma człowieków, więcej od 0 - są człowieki

    # If there are any human detections
    if len(human_detections) > 0:
        print("Human detected!")
        if not encoding:
            ttime = time.time()
            encoder.output = FileOutput(f"recordings/temp/{int(ttime)}_after.h264")
            picam2.start_encoder(encoder)
            encoding = True
            print("New Motion")
            out = cv2.VideoWriter(f"recordings/temp/{int(ttime)}_before.mp4", cv2.VideoWriter_fourcc(*'mp4v'), framerate, (w, h))
            for i in buffer:
                # changing XRGB to RGB
                j = np.zeros((h, w, 3), dtype=np.uint8) 
                j[..., 0] = i[..., 0]  
                j[..., 1] = i[..., 1]  
                j[..., 2] = i[..., 2]  
                out.write(j) #save frame to video file
            out.release()
        ltime = time.time()
    else:
        if encoding and time.time() - ltime > rtime:
            picam2.stop_encoder(encoder)
            print("Recording stop")
            encoding = False
            thread.start_new_thread(video_magic, (ttime,)) 
    
    if len(buffer) == buffer_size - 1:
            buffer.pop(0)

#################################################################
#                          Program run                          #
#################################################################
    
# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (800, 400)},
                                                     lores={"size": lsize, "format": "YUV420"}))
output = StreamingOutput()
encoder = H264Encoder(1000000)
picam2.set_controls({"FrameRate": framerate})
picam2.start_recording(JpegEncoder(), FileOutput(output))
picam2.start()

thread.start_new_thread(serverStart, ())

while True:
    # Capture a frame from camera
    frame = picam2.capture_array()
    
    # Process the frame with the function
    processed_frame = process_frame(frame) # Rozpoznawawnie ryja
    detect_human(frame) # Wykrywanie ludzia

    
# By breaking the loop we run this code here which closes everything
picam2.stop()
