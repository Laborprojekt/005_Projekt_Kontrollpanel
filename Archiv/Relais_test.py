from machine import Pin
import utime


rl_schuko_1 = Pin(9, Pin.OUT) #NO
rl_schuko_2 = Pin(10, Pin.OUT) #NO
rl_schuko_3 = Pin(11, Pin.OUT) #NO
rl_schuko_4 = Pin(12, Pin.OUT) #NO
rl_schuko_5 = Pin(13, Pin.OUT) #NO
rl_reboot = Pin(14,Pin.OUT)    #NC

schalter_display= Pin (35, Pin.IN, Pin.PULL_DOWN)
taster_schuko12 = Pin(37, Pin.IN, Pin.PULL_DOWN)
taster_schuko34 = Pin(39, Pin.IN, Pin.PULL_DOWN)

while True:
    
    if schalter_display.value() == 1:
        print("Schalter")
        
    if taster_schuko12.value() == 1:
        print("Taster 1")
        
    if taster_schuko34.value() == 1:
        print("Taster 2")
    '''
    
    rl_schuko_1.value(1)
    utime.sleep(1)

    rl_schuko_1.value(0)
    utime.sleep(1)
    
    rl_schuko_2.value(1)
    utime.sleep(1)
    
    rl_schuko_2.value(0)
    utime.sleep(1)
    
    rl_schuko_3.value(1)
    utime.sleep(1)
    
    rl_schuko_3.value(0)
    utime.sleep(1)
    
    rl_schuko_4.value(1)
    utime.sleep(1)
    
    rl_schuko_4.value(0)
    utime.sleep(1)
    
    rl_schuko_5.value(1)
    utime.sleep(1)
    
    rl_schuko_5.value(0)
    utime.sleep(1)
    
    rl_reboot.value(1)
    '''