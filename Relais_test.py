from machine import Pin
import utime

relais_1 = Pin(15, Pin.Out)

relais_1.value(1)
utime.sleep(2)

relais_1.value(0)
utime.sleep(2)

relais_1.value(1)
utime.sleep(2)

relais_1.value(0)
utime.sleep(2)