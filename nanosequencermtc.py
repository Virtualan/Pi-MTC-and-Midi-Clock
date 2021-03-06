import os, sys
import pygame
import pygame.midi
import pygame.fastevent
import time
import math
from pygame.locals import *
from serialmidi import *  
from korgnanocontrol import * 
from time import strftime
import sys
from random import random, choice, randrange, randint, sample
from mtc import *

sm = serialmidi()           # the serial midi port
knc = korgnanocontrol()     # the korg nanokontroller
clock = pygame.time.Clock()
miditimecode=mtc()
beat = 0 
oldbeat = 0
tempotime = 0
loopstart = 0
loopbeat = 0
loopend = 7
varyspeed = False
kick = False
snare = False
beatlimit = 20000
random_loopend = False
channel = 1
type = 9
data1 = 65
data2 = 127
ctrl = 1
jix = 2
scanrange = range(0,8)
sequence = []
fadermem = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
nomem = (0,0,0)
beattime = clock.get_time()
knobmem = [0,0,0,0,0,0,0,0]
self_randomize = True
self_randomizing = True
s_buttons = [False,False,False,False,False,False,False,False]
r_buttons = [True,True,True,True,True,True,True,True]

def read_nano(channel):
    #scan faders
    data1,data2 = knc.read_data()
    for control in scanrange:
        if data1 == 21+control:
            knobmem[control]=data2
        if data1 == 100+control:
            fadermem[channel-1][control]=data2
    return data1,data2

for n in range(1,9):
    sm.send_message("cc",n,123,0)  # all notes off all channels    
    sm.send_message(12,n,randint(0,68)) # random instruments

#MAIN LOOP   
while beat < beatlimit:
    # Hold until midi clock byte is received
    while True:
        checkbyte = miditimecode.get_midiclock()
        if checkbyte == "0xfc":  # master sequencer has sent stop
            knc.close()
            sys.exit()
        if checkbyte == "0xf8" and tempotime < 5:  # only go on every 4th tick 
            tempotime += 1
            pass
        else:
            tempotime = 0
            dt = clock.tick(1000)
            bpm=int(clock.get_fps()*60/4)
            print "BPM:",bpm,"Beat:",beat,"Ch:",channel,"F:", fadermem[channel-1],"K:",knobmem, "*" * len(sequence)
            break
            
    if self_randomize and beat % 48 == 0: 
        self_randomizing = not self_randomizing
        knc.send_data(0xB0,61,self_randomizing)
    
    scanrange = range(0,loopend+1)
    
    if beat == 128: kick = True
    if beat == 256: snare = True    
    
    data1,data2 = read_nano(channel)
    
    if data1 <> 0: print data1 # for diagnostics
    
    knc.send_data(0xB0,40+loopbeat,fadermem[channel-1][loopbeat])  # loopbeat light on if its not 0
    knc.send_data(0xB0,48+loopbeat,True)
    
    if data1 == 61 and data2 == 0: 
        self_randomize = not self_randomize
        knc.send_data(0xB0,61,self_randomizing)
    
    if data1 == 56 and data2 == 0: 
        delay += 0.1
        olddelay = delay
        
    if data1 == 57 and data2 == 0: 
        if delay > 0.1: delay -= 0.1
        olddelay = delay
        
    if self_randomizing:
        
        if not beat % 16: 
            jix = int(choice(['1','2','3','4','5']))
        else:
            jix = 4
        
        if random() > 0.96 and channel > 2:
            sm.send_message("cc",channel,0,0)
            bankchange = randint(0,6)
            sm.send_message("cc",channel,32,bankchange) #bank change
        
        if random_loopend and random()>0.5 and not beat % 8: #change loopend
            loopend = int(choice("0134567"))
            if loopstart > loopend: loopstart = 0
            scanrange = range(loopstart,loopend+1)
            sm.send_message("cc",channel,123,0)  # all notes off 
            #print ">>>>Loop set to :" + str(loopend) + "<<<<"            
        
        if random_loopend and random()>0.5 and not beat % 8: #change loopstart
            loopstart = randint (0,7)
            if loopstart > loopend: loopstart = loopend - randint(0,7)
            if loopstart < 0: 
                loopstart = 0
                loopend = 7
            scanrange = range(loopstart,loopend+1)
            sm.send_message("cc",channel,123,0)  # all notes off 
            #print ">>>>Loop start set to :" + str(loopstart) + "<<<<"         
            
        if varyspeed and random()>0.5 and not beat % 16: #Slow down
            if delay > 0.01:delay -= 0.1
            knc.send_data(0xB0,57,True)
            print "Slow Down"
        else:
            if varyspeed and random()>0.5 and not beat % 16: #Speed up
                delay += 0.1
                knc.send_data(0xB0,56,True)
                print "Speed Up"
               
        if random() > 0.897 and fadermem[channel-1][0] > 0:  # 3 note scale up
            #print "Set 3 note riser scale on channel:", channel
            for sc in range(0,7):
                if sc > 0 and fadermem[channel-1][sc] > 0:
                    fadermem[channel-1][sc]=fadermem[channel-1][0]+sc
        
        if random() > 0.998 and fadermem[channel-1][0] > 0:  # 5 note scale up
            #print "Set 5 note riser scale on channel:", channel
            for sc in range(0,7):
                if sc > 0 and fadermem[channel-1][sc] > 0:
                    fadermem[channel-1][sc]=fadermem[channel-1][0]+3*sc
        
        if random() > 0.999:  # 3 note scale down
            #print "Set 3 note downer scale on channel:", channel
            for sc in range(0,7):
                if sc > 0 and fadermem[channel-1][sc] > 0:
                    fadermem[channel-1][sc]=fadermem[channel-1][0]-sc
        
        # change program
        if random() > 0.5:
            if not beat % 4:
                knobmem[channel-1] += randint(0,20)
                if knobmem[channel-1] > 127: 
                    knobmem[channel-1] = 1
        
        if random() > 0.5:
            if not beat % 8:
                knobmem[channel-1] -= randint(0,20)    
                if knobmem[channel-1] < 0: 
                    knobmem[channel-1] = 1
        
        if random() > 0.5 and not beat % 2:     # random note 
            #print "Random Note on Channel " + str(channel) + " Beat " + str(loopbeat)
            if fadermem[channel-1][loopbeat] == 0:
                fadermem[channel-1][loopbeat] += 36
            
            if random() > 0.2:
                fadermem[channel-1][loopbeat] += int(choice(['1','2','3','5','7','9','12']))
            else:
                fadermem[channel-1][loopbeat] -= int(choice(['3','5','7','9','12']))
            for k in scanrange:
                knc.send_data(0xB0,32+k,False)     
                
        if random() > 0.5 and not beat % 3:     # random note 
            #print "Random Note on Channel " + str(channel) + " Beat " + str(loopbeat)
            if fadermem[channel-1][loopbeat] == 0:
                fadermem[channel-1][loopbeat] += 48
            
            if random() > 0.2:
                fadermem[channel-1][loopbeat] += int(choice(['12','8','7','9',]))
            else:
                fadermem[channel-1][loopbeat] -= int(choice(['5','6','9',]))
            for k in scanrange:
                knc.send_data(0xB0,32+k,False)             
        
        ####  random pan !!
        if random() > 0.3 and not beat % 2:   ## random Pan
            sm.send_message("cc",randint(1,8),10,randint(64-40,64+40))
    
        if random() > 0.99 and not beat % 16:   ## all notes off on random channel
            sm.send_message("cc",randint(1,8),123)
        
        if random() > 0.5 and not beat % 8:   ## random Channel Volume 
            sm.send_message("cc",channel,7,randint(64-10,64+10))
    
        
        if random() > 0.9:   #random null note
            ##print "Note Off on Channel " + str(channel) + " Beat " + str(loopbeat)
            fadermem[channel-1][loopbeat]=0
        
        #random channel change
        if random() > 0.9:     #random channel in faders loop area
            channel = randint(loopstart+1,loopend+1)  #select channel
            #print "Working on Channel: " + str(channel)
    
        # drum stuff
        if snare and loopend-loopstart == 3 and not beat % 4: 
            snare = False
        else:
            if loopend-loopstart > 3 and beat % 4 and beat > 256: 
                snare = True
    
        #end of random section
    
    # NanoKontrol input controls
    
    #cycle button
    if data1 == 60 and data2 == 0:
        random_loopend = not random_loopend
        knc.send_data(0xB0,60,random_loopend) 
        
    #set button
    if data1 == 64:
        for s in scanrange:
            fadermem[channel-1][s]=randint(24,96)
    
    #the small < button
    if data1 == 65:
        for s in scanrange:
            knobmem[s]=randint(24,96)
            sm.send_message(12,s+1,knobmem[s])
    
    #knobs to change channel if turned and store program number
    if data1 >20 and data1 <29:
        sm.send_message(12,channel,knobmem[channel-1])
        channel = data1-20
        for k in scanrange:
            knc.send_data(0xB0,32+k,False)   
    
    #s buttons
    if data1 >31 and data1 < 40:
        channel = data1-31
        for s in scanrange:
            knc.send_data(0xB0,32+s,False)    
    
    #m buttons to change loopend
    if data1 >39 and data1 < 48:
        loopend = data1-40
        scanrange = range(loopstart,loopend+1)
    
    #r buttons to show sequence step
    if data1 >47 and data1 < 56 and data2 == 0:
        r_buttons[data1-48] = not r_buttons[data1-48]
        
    #the small > button
    if data1 == 66 and data2 == 0:
        varyspeed = not varyspeed
        
    #play all 8 arrays ch1 - ch8 
    for ch in scanrange:                                                                        ###### play notes
        
        if fadermem[ch][loopbeat] > 0 and not beat % jix and random() > 0.5:  #play notes
            sm.send_message(12,ch+1,knobmem[ch])
            sm.send_message(type,ch+1,fadermem[ch][loopbeat]+12,randint(30,127))
            x = fadermem[ch][loopbeat]+12
            sq = (ch,x,channel)
            sequence.append(sq)   
        
        if fadermem[ch][loopbeat] > 0:  #play notes
            sm.send_message(12,ch+1,knobmem[ch])
            sm.send_message(type,ch+1,fadermem[ch][loopbeat],randint(30,127))
            x = fadermem[ch][loopbeat]
            sq = (ch,x,channel)
            sequence.append(sq)   
            
            # if random() > 0.9:
                # sm.send_message(8,ch+1,fadermem[ch][loopbeat]) # fast note off
            
            if random()>0.5 and not ch % 2 : # play major triad
                sm.send_message(type,ch+1,fadermem[ch][loopbeat]+4,randint(30,127))
                sq = (ch,x+4,channel)
                sequence.append(sq)
                sm.send_message(type,ch+1,fadermem[ch][loopbeat]+7,randint(30,127))
                sq = (ch,x+7,channel)
                sequence.append(sq)
            else:    
                if random() > 0.5 and beat % 2 and not ch % 3: # play minor 7th 
                    sm.send_message(type,ch+1,fadermem[ch][loopbeat]+3,randint(30,127))
                    sq = (ch,x+3,channel)
                    sequence.append(sq)
                    sm.send_message(type,ch+1,fadermem[ch][loopbeat]+8,randint(30,127))
                    sq = (ch,x+8,channel)
                    sequence.append(sq)    
                else:
                    if random() > 0.5 and ch % 4: # play major 9th 
                        sm.send_message(type,ch+1,fadermem[ch][loopbeat]+4,randint(30,127))
                        sq = (ch,x+4,channel)
                        sequence.append(sq)
                        sm.send_message(type,ch+1,fadermem[ch][loopbeat]+9,randint(30,127))
                        sq = (ch,x+9,channel)
                        sequence.append(sq)    
            
            #random additional drum notes
            if ch == 0 or ch == 1 or ch == 3:
                if random() > 0.8:
                    sm.send_message(type,10,fadermem[ch][loopbeat],randint(20,100))  #play some percussion 
                    sm.send_message(8,10,fadermem[ch][loopbeat])  # drum note off 
    
    #steady drum beat 
    if (loopend-loopstart > 1) and not beat % 4: 
        sm.send_message(type,10,46,randint(70,100))  #play some percussion (HHO) 
        
    if (loopend-loopstart > 1) and (loopend-loopstart <= 4) and beat % 4 and random() > 0.2: 
        sm.send_message(type,10,42,randint(50,100))  #play some percussion (HHC) 
    
    if (loopend-loopstart > 1) and beat % 2 and random() > 0.2: 
        sm.send_message(type,10,42,randint(50,100))  #play some percussion (HHC) 
    
    if data1 == 62 and data2 == 0:
        kick = not kick
        
    if kick and not beat % jix:
        sm.send_message(type,10,35,randint(70,120))  #play some percussion  (kick)
        sm.send_message(8,10,35) 
    
    if kick and not beat % 8:
        sm.send_message(type,10,36,randint(70,120))  #play some percussion  (kick)
        sm.send_message(8,10,36) 
    
    if data1 == 63 and data2 == 0 and beat > 256:
        snare = not snare
        
    if snare and not beat % (jix * 2) and beat > 256:
        sm.send_message(type,10,38,randint(70,120))  #play some percussion (Snare)
        sm.send_message(8,10,38) 
    
    ### sustained notes
    if len(sequence) > 5:
        for no in range(0,len(sequence)-(int(random()*5))):
            cx,nomem,channel = sequence.pop(0)
            sm.send_message(8,cx+1,nomem,0) ### note off
    
    ### short notes
    if random() > 0.5:
        if len(sequence) > 2:
            for no in range(0,len(sequence)-(int(random()*2))):
                cx,nomem,channel = sequence.pop(0)
                sm.send_message(8,cx+1,nomem,0) ### note off
    
    #update the nano lights
    knc.send_data(0xB0,40+loopbeat,False)  #loopbeat light off
    knc.send_data(0xB0,48+loopbeat,False)  #loopbeat light off
    knc.send_data(0xB0,32+channel-1,loopbeat % 4)
    knc.send_data(0xB0,59,beat % 2)
    knc.send_data(0xB0,56,False)
    knc.send_data(0xB0,57,False)
    
    loopbeat += 1
    
    if loopbeat > loopend: loopbeat = loopstart
    
    # Stop Button
    if data1 == 58:
        knc.send_data(0xB0,58,0) #turn stop light off
        knc.send_data(0xB0,59,0) #turn play light off
        knc.send_data(0xB0,61,0) #turn cycle light off
        knc.send_data(0xB0,60,0) 
        break
    
    beat = beat + 1
    # Random loopend-loopstart
    if beat % 128 == 0: 
        random_loopend = not random_loopend
        knc.send_data(0xB0,60,random_loopend)
        if not random_loopend:
            loopstart = 0
            loopend = 7
            scanrange = (loopstart,loopend)

#we have broke out of the loop (stopped)            
for n in range(1,9):
    sm.send_message("cc",n,123,0)  # all notes off all channels
#close port or we will get error    
knc.close()
