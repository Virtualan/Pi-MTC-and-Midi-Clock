import time
import serial
import threading

class mtc():
    
    def __init__(self):
        self.ser=serial.Serial('/dev/ttyAMA0',38400)		# Set up the UART - my pi midiport  
        self.get_time_now = time.time()
        self.byteindex = 0
        self.threadsDieNow=False
        
    def start_mtc(self):
        # starts multitask process to start running forever.
        self.gmtc = threading.Thread(target=self.gen_mtc)
        self.gmtc.start()
    
    def get_midiclock(self):
        self.midi_in_byte=hex(ord(self.ser.read()))
        if self.midi_in_byte == "0xf8" or self.midi_in_byte == "0xfc":
            return self.midi_in_byte
        
    def get_midibyte(self):
        self.midi_in_byte=hex(ord(self.ser.read()))
        return self.midi_in_byte    

    def get_midimessage(self):
        self.midi_in_message=self.ser.read(3)
        h = ord(self.midi_in_message[0])
        b1 = ord(self.midi_in_message[1])
        b2 = ord(self.midi_in_message[2])
        return h,b1,b2    
        
    def gen_mtc(self,forever=True):
        while forever:
            if self.threadsDieNow: break
            
            #split the current time since we started this
            self.t = time.time() - self.get_time_now
            self.h = int(self.t/3600)
            self.t -= self.h*3600
            self.m = int(self.t/60)
            self.t -= self.m*60
            self.s = int(self.t)
            self.t -= self.s
            self.frames = float(self.t / (1.0/25.0))  # Set at 25 FPS
            self.f = int(self.frames)
            self.sf = int((self.frames - self.f)*100)
            
            #set up the MTC bytes using the above
            self.byte0 = chr(0xF1) + chr(0x00 + (self.f & 0x0f))
            self.byte1 = chr(0xF1) + chr(0x10 + (self.f >> 4))
            self.byte2 = chr(0xF1) + chr(0x20 + (self.s & 0x0f))  
            self.byte3 = chr(0xF1) + chr(0x30 + (self.s >> 4))  
            self.byte4 = chr(0xF1) + chr(0x40 + (self.m & 0x0f))
            self.byte5 = chr(0xF1) + chr(0x50 + (self.m >> 4)) 
            self.byte6 = chr(0xF1) + chr(0x60 + (self.h & 0x0f))
            self.byte7 = chr(0xF1) + chr(0x72 + (self.h >> 4))  # 0x72 = 25 FPS
            self.mm = [self.byte0,self.byte1,self.byte2,self.byte3,self.byte4,self.byte5,self.byte6,self.byte7] 
            
            #don't send to fast - YMMV may require tweaking
            time.sleep(0.00125)
            
            #only send every quarter frame
            if self.sf > 0 and self.sf < 25: 
                self.ser.write(self.mm[self.byteindex])
                self.byteindex += 1 
            
            #send byte0 to byte7 repeatedly     
            if self.byteindex > 7: self.byteindex = 0
            
            #stop if told
            if forever==False: break
    
    def stop_mtc(self):
        self.threadsDieNow = True
        self.forever = False
    
  
