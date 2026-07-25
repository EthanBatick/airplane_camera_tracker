import time
from machine import UART, Pin, PWM

heading_offset = 0 # how you position the tracker physically eg pointing due east is 0 offset

time.sleep(0.1) # Wait for USB to become ready

WAIT_UART_MS = 100

# , tx=Pin(4), rx=Pin(5),
uart0 = UART(0, baudrate=115200, timeout=WAIT_UART_MS)
led = Pin('LED', Pin.OUT, value=0)
buf = b''

### SERVO STUFF ###

heading_servo = PWM(Pin(16))
heading_servo.freq(50)
lh = 1200
hh = 7600
tuneh = 0

inclination_servo = PWM(Pin(17))
inclination_servo.freq(50)
li = 1320
hi = 7850
tunei = 0

master_heading = 90
master_inclination = 45

###################
while (True):
    # Read any characters available from the UART, wait up to WAIT_UART_MS ms
    chunk = uart0.read()

    # If there is nothing new, just start the loop over (uart0.read())
    if not chunk:
        continue

    # Append the new data to the buffer
    buf += chunk

    # Parse the buffer contents
    while True:
        # Search for a carriage return
        idx = buf.find(b'\r')
        if idx < 0:
            # If no CR, exit the loop early
            break
        # Get the substring from the beginning of the buffer up to the CR
        token = buf[:idx]
        # Update the buffer to remove the parsed token
        buf = buf[idx+1:]
        # Pass the token to the command runner
        decoded_payload = token.decode().split(",")
        master_heading = float(decoded_payload[0])%180.0
        master_inclination = float(decoded_payload[1])%180.0
        
        #### MORE SERVO STUFF ####
        print(master_heading, master_inclination)

        dutyh = int(lh + ((hh-lh) * (1-((master_heading - heading_offset)/180.0))))
        heading_servo.duty_u16(dutyh + tuneh)
        
        dutyi = int(lh + ((hh-lh) * (1-((master_inclination+90)/180.0))))
        inclination_servo.duty_u16(dutyi + tunei)
        
        ##########################
        
        break
