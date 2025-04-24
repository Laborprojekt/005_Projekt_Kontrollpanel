'''
Name:           Kontrollpanel
Datum:          25.03.2025
Version:        1.0

Entwickler:     Eberlei

Hardware:
- ESP32-S3-DevKitC-1
- SRD-03VDC-SL-C (NC)
- SRD-03VDC-SL-C (NO)
- AHT20
- Shelly plus 1 PM
- ST7789V3, 1.69", 240x280p
'''

from machine import Pin, SoftI2C, SoftSPI
import utime
import ujson
import network
from umqtt.simple import MQTTClient
import aht10
import st7789py as st7789
import vga2_16x16 as font

#---------------- Pin ----------------#

rl_reboot = Pin(14,Pin.OUT)    #NC
rl_schuko_1 = Pin(13, Pin.OUT) #NO
rl_schuko_2 = Pin(12, Pin.OUT) #NO
rl_schuko_3 = Pin(11, Pin.OUT) #NO
rl_schuko_4 = Pin(10, Pin.OUT) #NO
rl_schuko_5 = Pin(9, Pin.OUT) #NO

taster_display= Pin (35, Pin.IN, Pin.PULL_DOWN)
taster_schuko12 = Pin(37, Pin.IN, Pin.PULL_DOWN)
taster_schuko34 = Pin(39, Pin.IN, Pin.PULL_DOWN)

i2c = SoftI2C(sda = 41, scl = 42)

########## SPI Bus konfigurieren ##########

spi = SoftSPI(
        baudrate=40000000,
        polarity=1,
        phase=0,
        sck=Pin(4),    # scl
        mosi=Pin(5),   # sda
        miso=Pin(0))    # wird nicht angeschlossen

# Falls die SPI Pins falsch sind, "print (machine.SPI(1))" gibt die Pinnummern vom ESP aus

########## DisplayObjekt erstellen ##########

tft = st7789.ST7789(
        spi,
        240,
        320,
        reset=Pin(6, Pin.OUT),
        cs=Pin(15, Pin.OUT),
        dc=Pin(7, Pin.OUT),
        backlight=Pin(16, Pin.OUT),
        rotation=1)

#---------------- Variablen ----------------#

reboot = False
schuko12 = False
schuko34 = False

schuko1 = False
schuko2 = False
schuko3 = False
schuko4 = False

time_irq_schuko12 = 0
time_irq_schuko34 = 0


voltage, current, power, energy, mid_temp, mid_hum  = 0, 0, 0, 0, 0, 0
prev_voltage, prev_current, prev_power, prev_energy, prev_temp, prev_hum  = 0, 0, 0, 0, 0, 0

shelly_energy = {}

cycle_time_ms = 0

# Sensor
aht = aht10.AHT10(i2c = i2c)

# Allgemein
temp_list = []
hum_list = []
last_aht_check = 0
INTERVALL_MS_AHT = 10000

INTERVALL_MS_TASTER = 2000

# Display
SNOWFLAKE ="*****************"
BOOT = "boot successfull"
CLEAR = "                             "
START_TEXT = 35      # x
START_TEXT_MEASUREMENT = 20
SECUNDARY_TEXT = 140 # x
INTERVALL_MS_DISPLAY_UPDATE = 6000 # Shelly sendet alle 10s Daten
DISPLAY_SHUTDOWN_TIME_MS = 180000 # Zeit nach der sich das Display automatisch abschaltet
display_on_timestamp_ms = 0 # Timestamp für automatische abschaltung
display_state = False
display_activation_time = 0 # Entprellung interrupt
display_update_time = 0 # Timestamp der letzten aktualisierung


#---------------- MQTT-Konfiguration ----------------#
CLIENT_ID_relais = "ESP_Relais"
CLIENT_ID_shelly = "ESP_Shelly"
CLIENT_ID_ESP = "ESP_send"
MQTT_TOPIC_relais = "dashboard_switch"
MQTT_TOPIC_shelly = "shelly"
MQTT_TOPIC_AHT = "AHT"
MQTT_TOPIC_LOG = "logs"

# @home
WIFI_SSID = "502-Bad-Gateway"
WIFI_PASSWORD = "66813838796323588312"
MQTT_SERVER = "192.168.188.26"   #Achtung: aktuelle Adresse des Brokers!

# @BZTG
#WIFI_SSID = "BZTG-IoT" 
#WIFI_PASSWORD = "WerderBremen24"
#MQTT_SERVER = "192.168.1.195"   #Achtung: aktuelle Adresse des Brokers!

BAUGRUPPE = "Kontrollpanel" # Info für JSON

#---------------- Funktion zur Datenauswertung ------------- 
def sub_relais(topic, msg):
    global reboot, schuko12, schuko34, schuko1, schuko2, schuko3, schuko4
    
    daten = ujson.loads(msg)
    print("sub_relais")
    
    reboot_value, schuko12_value, schuko34_value, schuko1_value, schuko2_value, schuko3_value, schuko4_value = 0,0,0,0,0,0,0

    try:
        reboot_value = daten.get("reboot")
        schuko12_value = daten.get("schuko12")
        schuko34_value = daten.get("schuko34")
        schuko1_value = daten.get("schuko1")
        schuko2_value = daten.get("schuko2")
        schuko3_value = daten.get("schuko3")
        schuko4_value = daten.get("schuko4")
        print(reboot_value)
        print(schuko12_value)
        print(schuko34_value)
        print(schuko1_value)
        print(schuko2_value)
        print(schuko3_value)
        print(schuko4_value)
    except:
        pass
  

    if reboot_value:
        reboot = not reboot
    
    if schuko12_value:
        schuko12 = not schuko12
        
        schuko1 = schuko12
        schuko2 = schuko12
        
    if schuko34_value:
        schuko34 = not schuko34
        
        schuko3 = schuko34
        schuko4 = schuko34
         
    if schuko1_value:
        schuko1 = not schuko1
        
    if schuko2_value:
        schuko2 = not schuko2
        
    if schuko3_value:
        schuko3 = not schuko3
        
    if schuko4_value:
        schuko4 = not schuko4
        
    
def sub_shelly(topic, msg):  
    daten = ujson.loads(msg) 
    
    global shelly_energy, voltage, current, power, energy
    shelly_energy = daten
    
    voltage = shelly_energy.get("voltage")
    current = shelly_energy.get("current")
    power = shelly_energy.get("power")
    energy = shelly_energy.get("energy")
    
    print(shelly_energy, voltage, current, power, energy)


def mqtt_publish(json_data, topic):
    
    # MQTT-Broker Adresse
    client = MQTTClient(CLIENT_ID_ESP, MQTT_SERVER, port=1883)
    
    client.connect()  # Verbindung zum Broker aufbauen
    print("Verbunden mit MQTT-Broker")

    # Nachricht an Topic senden
    client.publish(topic, json_data)
    print(f"Nachricht veröffentlicht: {json_data} an Topic: {topic}")

    client.disconnect()
    

def schuko12_irq(pin):
    global schuko12, schuko1, schuko2, time_irq_schuko12
    timestamp = utime.ticks_ms()

    if timestamp - time_irq_schuko12 >= INTERVALL_MS_TASTER:
        print("schuko12 interrupt")
        
        schuko12 = not schuko12
        
        schuko1 = schuko12
        schuko2 = schuko12
        
        time_irq_schuko12 = timestamp
   
   
def schuko34_irq(pin):
    global schuko34, schuko3, schuko4, time_irq_schuko34
    timestamp = utime.ticks_ms()
    
    if timestamp - time_irq_schuko34 >= INTERVALL_MS_TASTER:
        print("schuko34 interrupt")
        
        schuko34 = not schuko34
        
        schuko3 = schuko34
        schuko4 = schuko34
        
        time_irq_schuko34 = timestamp
     
     
def mittelwert (value, value_list):
    value_sum = 0
    
    value_list.append(value)
    
    len_list = len(value_list)
    
    if len_list > 10:
        value_list.pop(0)
    
    copy_list = value_list[:]
    
    if len_list >= 3:
        copy_list.sort
        copy_list.pop(0)
        copy_list.pop()
    
    for i in copy_list:  
        value_sum += i
        
    mittelwert = int(value_sum/len(copy_list))
     
    return mittelwert, value_list


def store_data(timestamp, mid_temp, mid_hum):

    json_raw = {
            "Baugruppe" : BAUGRUPPE,
            "timestamp" : timestamp,
            "Sensorwerte" :
                {
                "temp" : mid_temp,
                "hum" : mid_hum,
                }
            }   
    
    json_data = ujson.dumps(json_raw)

    return json_data
    
def clear_boot():
    tft.fill_rect(0,105,320,25, st7789.BLACK) #x,y,width,height
    
    
def log_display(text):
    
    tft.text(font, CLEAR , START_TEXT, 90, st7789.WHITE, st7789.BLACK)
    tft.text(font, "- LOG -" , 100, 90, st7789.WHITE, st7789.BLACK)    
    
    tft.text(font, CLEAR , START_TEXT, 120, st7789.WHITE, st7789.BLACK)
    tft.text(font, text , START_TEXT, 120, st7789.WHITE, st7789.BLACK)
    
    
def show_display(pin=0): # Pin =0 hat vordefiniert werte, um die Funktion außerhalb des interrupt verwenden zu können
    
    global display_state
    global display_activation_time
    
    time = utime.ticks_ms()
    
    if time - display_activation_time >= 3000:
        
        if tft.backlight.value() == 0:
            
            display_state = True
            print(display_state)
            print("Display on")
            
            display_activation_time = utime.ticks_ms()
            
        else:
            display_off()
        
def display_off(pin=0): # Pin =0 hat vordefiniert werte, um die Funktion außerhalb des interrupt verwenden zu können
    
    global display_state
    
    display_state = False
    tft.backlight.value(0)
    tft.fill(st7789.BLACK)
    tft.sleep_mode(True)
    print("Display off")
    
def timestamp_generator():
    clock = utime.localtime()
    timestamp = f"{clock[0]}-{clock[1]}-{clock[2]}T{clock[3]}:{clock[4]}:{clock[5]}_MEZ"
    
    return timestamp

def log(eventtype, log_message):
    
    global MQTT_TOPIC_LOG
    
    json_raw = {
            "eventtype" : eventtype,
            "event_text" : log_message
            }
    
    json_data = ujson.dumps(json_raw)
    
    mqtt_publish(json_data, MQTT_TOPIC_LOG)
    

#---------------- Funktion WIFI -------------------------------------------
def connectWIFI(): 
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True) 
    wlan.connect(WIFI_SSID, WIFI_PASSWORD) 
    while not wlan.isconnected(): 
        pass 
    print ("wifi connected")   
    print(wlan.ifconfig()) # WIFI verbinden   


#---------------- Interrupts ---------------------------------------------- 
taster_display.irq(trigger = Pin.IRQ_RISING, handler = show_display)
#taster_display.irq(trigger = Pin.IRQ_RISING or Pin.IRQ_FALLING, handler = show_display)
#taster_display.irq(trigger = Pin.IRQ_FALLING, handler = display_off)
taster_schuko12.irq(trigger = Pin.IRQ_FALLING, handler = schuko12_irq)
taster_schuko34.irq(trigger = Pin.IRQ_FALLING, handler = schuko34_irq)


#---------------- Boot Display --------------------------------------------
tft.backlight.value(1)
tft.fill(st7789.BLACK)

tft.text(font, SNOWFLAKE , 20, 30, st7789.WHITE, st7789.BLACK)
tft.text(font, BOOT , 35, 110, st7789.WHITE, st7789.BLACK)
tft.text(font, SNOWFLAKE , 20, 190, st7789.WHITE, st7789.BLACK)

utime.sleep(1)
clear_boot()


# -------- MQTT-Client erzeugen, Callback festlegen und Topic abonnieren --
   
connectWIFI()

mqtt_relais = MQTTClient(CLIENT_ID_relais, MQTT_SERVER)
mqtt_relais.set_callback(sub_relais) 
utime.sleep(1) 
mqtt_relais.connect() 
mqtt_relais.subscribe(MQTT_TOPIC_relais)
log_display("- MQTT relais")
log("MQTT", "relais verbunden")
print("MQTT relais verbunden!")

utime.sleep(1)

mqtt_shelly = MQTTClient(CLIENT_ID_shelly, MQTT_SERVER)
mqtt_shelly.set_callback(sub_shelly) 
utime.sleep(1) 
mqtt_shelly.connect() 
mqtt_shelly.subscribe(MQTT_TOPIC_shelly)

log_display("- MQTT shelly")
log("MQTT", "shelly verbunden")
print("MQTT shelly verbunden!")

utime.sleep(1)

display_off()

log("Systemstatus", "Controller online, start loop")

#---------------- Hauptprogramm ------------------------------------------- 
while True:
    cycle_time_ms = utime.ticks_ms() # Zykluszeit
    
    try:
        mqtt_relais.check_msg()
    
    except Exception as e:
        log("mqtt_relais check error", e)
    
    try:
        mqtt_shelly.check_msg()
    
    except Exception as e:
        log("mqtt_shelly check error", e)
        
    utime.sleep(1)

#---------------- Relais schalten ----------------------------------------- 
    rl_reboot.value(reboot)
    rl_schuko_1.value(schuko1)
    rl_schuko_2.value(schuko2)
    rl_schuko_3.value(schuko3)
    rl_schuko_4.value(schuko4)

#---------------- AHT Messung ---------------------------------------------
    try:
        if cycle_time_ms - last_aht_check >= INTERVALL_MS_AHT:
            
            last_aht_check = utime.ticks_ms()
            # Messwerte erheben
            temp = aht.temperature()
            hum = aht.humidity()
            
            timestamp = timestamp_generator()
            
            # Mittelwerte bilden 
            mid_temp, temp_list = mittelwert(temp, temp_list)
            mid_hum, hum_list = mittelwert(hum, hum_list)
            
            json_data = store_data(timestamp, mid_temp, mid_hum)
            
            mqtt_publish(json_data, MQTT_TOPIC_AHT)
            
            print("AHT data send")
    except Exception as e:
        log("AHT error", e)
        
#---------------- Display einschalten -------------------------------------
    try:
        if display_state == True and cycle_time_ms - display_update_time >= INTERVALL_MS_DISPLAY_UPDATE:
            
            if cycle_time_ms - display_on_timestamp_ms <= DISPLAY_SHUTDOWN_TIME_MS: # automatische Abschaltung nach 3 Minuten (Änderungsparameter: DISPLAY_SHUTDOWN_TIME_MS)
            
                initial_run = False
                
                if tft.backlight.value() == 0:
                    display_on_timestamp_ms = utime.ticks_ms()
                
                    # Display einschalten
                    tft.sleep_mode(False)
                    tft.backlight.value(1)
                    
                    initial_run = True 
                    #initial_run = prev_temp == None # ändert den initial run parameter, wenn das display vorher ausgeschaltet war
                
                # ----- Messwerte anzeigen und aktulisieren -----
                if initial_run or voltage != prev_voltage:
                    prev_voltage = voltage
                    # Extra Leerzeichen sind zum überschreiben, falls vorheriger Wert mehr Zeichen hatte
                    tft.text(font, f"{voltage} V", START_TEXT_MEASUREMENT, 60, st7789.CYAN, st7789.BLACK)
                
                if initial_run or current != prev_current:
                    prev_current = current
                    if current >=10: # Rundet Ströme ab 10A, um max. 4 Zahlen auf dem Display anzuzeigen
                        current = round(current, 2)
                    tft.text(font, f"{current} A", START_TEXT_MEASUREMENT, 90, st7789.RED, st7789.BLACK)
                    prev_current = current
                    
                if initial_run or power != prev_power:
                    prev_power = power
                    tft.text(font, f"{power} W               ", START_TEXT_MEASUREMENT, 120, st7789.YELLOW, st7789.BLACK) 
                    
                if initial_run or energy != prev_energy:
                    prev_energy = energy
                    tft.text(font, f"{energy} Wh             ", START_TEXT_MEASUREMENT, 150, st7789.YELLOW, st7789.BLACK)            
                    
                if initial_run or mid_temp != prev_temp:
                    prev_temp = mid_temp
                    tft.text(font, f"Temp:{mid_temp} C", SECUNDARY_TEXT, 60, st7789.GREEN, st7789.BLACK)          
                    
                if initial_run or hum != prev_hum:
                    prev_hum = mid_hum
                    tft.text(font, f"Hum: {mid_hum} %", SECUNDARY_TEXT, 90, st7789.GREEN, st7789.BLACK)
        
            else: # automatische Abschaltung nach 3 Minuten (Änderungsparameter: DISPLAY_SHUTDOWN_TIME_MS)
                display_off() 
        
    except Exception as e:
        log("Display error", e)
