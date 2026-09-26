import serial
from time import sleep

class modem():
    def __init__(self):
        self.s_port = '/dev/ttyS0'
        self.s_baud = 9600
        
        connected = False
        self.retry = 0
        while not connected:
            connected = self.connect()
            if self.retry != 0 and not connected: 
                print("SERIAL:", "Connection not ready, retrying in 10 seconds")
                sleep(10)

    def connect(self):
        self.retry =+1
        print("SERIAL:", "Connecting to " + self.s_port + " using " + str(self.s_baud) + " speed")
        try:
            self.s = serial.Serial(self.s_port, self.s_baud)
            sleep(5)
            self.send_command("AT")
            modem = self.send_command("AT+CGMM")
            modem = modem.split("\n")[1]
            print("SERIAL <- MODEM:", "Connected to " + str(modem))
            return True
        except serial.SerialException as e:
            match(e.errno):
                case 2:
                    print("SERIAL:", "Connection failure: Device " + self.s_port + " does not exist")
                case 16:
                    print("SERIAL:", "Connection failure: Device already in use")
            return False
            

    def check_status(self):
        print("SERIAL -> MODEM:", "Checking registration status")
        log_base = "Registration status: "
        ready = 0
        while ready != 1:
            self.clean_serial()
            response = self.send_command("AT+CREG?")
            ready = int(response.split("\n")[1].split(",")[1].strip('\r')) 
            match ready:
                case 0:
                    print("SERIAL <- MODEM:", log_base + "Not registered, MT is not currently searching a new operator to register to")
                case 1:
                    print("SERIAL <- MODEM:", log_base + "Registered, home network")
                case 2:
                    print("SERIAL <- MODEM:", log_base + "Not registered, but MT is currently searching a new operator to register to")
                case 3:
                    print("SERIAL <- MODEM:", log_base + "Registration denied")
                case 4:
                    print("SERIAL <- MODEM:", log_base + "Unknown")
                case 5:
                    print("SERIAL <- MODEM:", log_base + "Registered, roaming")
            sleep(5)
    
    def clean_serial(self):
        response = self.s.read(self.s.inWaiting()).decode().strip()
    
    def send_command(self, command):
        self.s.write(command.encode() + b'\r\n')
        sleep(1)
        try:
            response = self.s.read(self.s.inWaiting()).decode().strip()
            return response
        except:
            print("Unknown Error")
    
    def send(self, number, message):
        self.check_status()

        print("SERIAL -> MODEM:", 'Changing modem SMS mode to "TEXT"')  
        self.send_command('AT+CMGF=1')  # Change modem SMS mode to

        print("SERIAL -> MODEM:", "Sending message to " + number)
        self.send_command('AT+CMGS="{}"'.format(number)) 
        self.s.write(message.encode() + b'\x1A')  # '\x1A' is the ASCII code for Ctrl+Z
        sleep(5)

    def receive(self):
        messages = list()
        print("SERIAL -> MODEM:", 'Changing modem SMS mode to "TEXT"')
        self.send_command('AT+CMGF=1')

        # Check if there are any new SMS messages
        print("SERIAL -> MODEM:", 'Checking if SMS is waiting for processing')
        response = self.send_command('AT+CMGL="ALL"')
        if "+CMGL:" in response:    
            # Parse and print received messages
            temp = response.split('+CMGL:') #
            for msg in temp[1:]:
                lines = msg.split('\n')   
                sender = lines[0].split(',')[2].strip('"')
                date = lines[0].split(',')[4].strip('"')
                time = lines[0].split(',')[5].strip('"')
                content = lines[1].strip()
                print("SERIAL <- MODEM:", "Received message from " + sender + ' at "' + date + " " + time[:-5] + '"')
                print("Sender:", sender)
                print("Date & Time:", date, time)
                print("Message:", content)
                print()
                message = {
                    'number': sender,
                    'content': content
                }
                messages.append(message)
                self.clean_cache() 
        else:
            print("SERIAL <- MODEM:", "SMS temporary storage is empty")
        
        return messages

    def clean_cache(self):
        self.send_command('AT+CMGD=0,1')