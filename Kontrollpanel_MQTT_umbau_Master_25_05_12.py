'''
Name:           Kontrollpanel
Datum:          12.05.2025
Version:        1.0

Entwickler:     Eberlei

Hardware:
- ESP32-S3-DevKitC-1
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

taster_display= Pin (35, Pin.IN)
taster_schuko12 = Pin(36, Pin.IN)
taster_schuko34 = Pin(37, Pin.IN)

i2c = SoftI2C(sda = 10, scl = 9)
aht = aht10.AHT10(i2c, address=0x38)

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
        reset=Pin(15, Pin.OUT),
        cs=Pin(18, Pin.OUT),
        dc=Pin(16, Pin.OUT),
        backlight=Pin(13, Pin.OUT),
        rotation=1)


#---------------- Variablen / Konstanten ----------------#

# Allgemein
cycle_time_ms = 0

time_irq_schuko12 = 0
time_irq_schuko34 = 0

INTERVALL_MS_TASTER = 2000


# Energiemessung
last_shelly_check_ms = 0
shelly_energy = {}
voltage, current, power, energy, mid_temp, mid_hum  = 0, 0, 0, 0, 0, 0
prev_voltage, prev_current, prev_power, prev_energy, prev_temp, prev_hum  = 0, 0, 0, 0, 0, 0
INTERVALL_MS_SHELLY_ENERGY = 3000


# AHT
temp_list = []
hum_list = []
last_aht_check = 0
INTERVALL_MS_AHT = 10000


# Display Variablen
display_on_timestamp_ms = 0 # Timestamp für automatische abschaltung
display_state = False
display_activation_time = 0 # Entprellung interrupt
display_update_time = 0 # Timestamp der letzten aktualisierung


# Display Konstanten
SNOWFLAKE ="*****************"
BOOT = "boot successfull"
CLEAR = "                             "
START_TEXT = 35      # x
START_TEXT_MEASUREMENT = 20
SECUNDARY_TEXT = 140 # x
INTERVALL_MS_DISPLAY_UPDATE = 6000 # Shelly sendet alle 10s Daten
DISPLAY_SHUTDOWN_TIME_MS = 180000 # Zeit nach der sich das Display automatisch abschaltet


#---------------- MQTT-Konfiguration ----------------#
CLIENT_ID_relais = "ESP_Relais_Master"
CLIENT_ID_shelly = "ESP_Shelly_Master"
CLIENT_ID_ESP = "ESP_send_Master"
MQTT_TOPIC_relais = "node-red_relais_button"
MQTT_TOPIC_shelly_energy = "shelly_energydata"
MQTT_TOPIC_AHT = "ESP_AHT"
MQTT_TOPIC_LOG = "ESP_logs"

# @home
WIFI_SSID = "502-Bad-Gateway"
WIFI_PASSWORD = "66813838796323588312"
MQTT_SERVER = "192.168.188.26"   #Achtung: aktuelle Adresse des Brokers!

# @BZTG
#WIFI_SSID = "BZTG-IoT" 
#WIFI_PASSWORD = "WerderBremen24"
#MQTT_SERVER = "192.168.1.195"   #Achtung: aktuelle Adresse des Brokers!

BAUGRUPPE = "ESP_Master" # Info für JSON

#---------------- Funktion zur Datenauswertung ------------- 
        
# Liest die relevanten Informationen aus den Shelly Energiedaten aus, die per MQTT empfangen wurden
def sub_shelly(topic, msg):  
    daten = ujson.loads(msg) 
    
    global shelly_energy, voltage, current, power, energy
    shelly_energy = daten
    
    voltage = shelly_energy.get("voltage")
    current = shelly_energy.get("current")
    power = shelly_energy.get("power")
    energy = shelly_energy.get("energy")
    
    print(shelly_energy, voltage, current, power, energy)


# Sendet beliebige Daten an den MQTT Broker
def mqtt_publish(json_data, topic):
    
    # MQTT-Broker Adresse
    client = MQTTClient(CLIENT_ID_ESP, MQTT_SERVER, port=1883)
    
    client.connect()  # Verbindung zum Broker aufbauen
    print("Verbunden mit MQTT-Broker")

    # Nachricht an Topic senden
    client.publish(topic, json_data)
    print(f"Nachricht veröffentlicht: {json_data} an Topic: {topic}")

    client.disconnect()
    
    
# Interrupt Handler für den Taster der Steckdosengruppe 1
def schuko12_irq(pin):
    
    try:
        global time_irq_schuko12, BAUGRUPPE
        timestamp = utime.ticks_ms()
        time = timestamp_generator()
        
        if timestamp - time_irq_schuko12 >= INTERVALL_MS_TASTER:
            print("schuko12 interrupt")
            
            json_raw = {
                "Baugruppe" : BAUGRUPPE,
                "timestamp" : time,
                "schuko12" : True
                }   
        
            json_data = ujson.dumps(json_raw)
            
            mqtt_publish(json_data, MQTT_TOPIC_relais)
            
            time_irq_schuko12 = timestamp
        
    except Exception as e:
        log("Master schuko12.irq error", e)


# Interrupt Handler für den Taster der Steckdosengruppe 2
def schuko34_irq(pin):
    
    try: 
        global time_irq_schuko34, BAUGRUPPE
        timestamp = utime.ticks_ms()
        
        time = timestamp_generator()
        
        
        if timestamp - time_irq_schuko34 >= INTERVALL_MS_TASTER:
            print("schuko34 interrupt")
            
            json_raw = {
                "Baugruppe" : BAUGRUPPE,
                "timestamp" : time,
                "schuko34" : True
                }   
        
            json_data = ujson.dumps(json_raw)
            
            mqtt_publish(json_data, MQTT_TOPIC_relais)
            
            time_irq_schuko34 = timestamp
            
    except Exception as e:
        log("Master schuko34.irq error", e)
     
     
# Ermittlung der Mittelwerte für die AHT Messwerte, über 10 Messzyklen        
def mittelwert (value, value_list):
    value_sum = 0
    
    value_list.append(value)
    
    len_list = len(value_list)
    
    if len_list > 10:
        value_list.pop(0)
    
    copy_list = value_list[:] # erzeugt eine pyhsische kopie Liste
    
    if len_list >= 3:
        copy_list.sort
        copy_list.pop(0)
        copy_list.pop()
    
    for i in copy_list:  
        value_sum += i
        
    mittelwert = int(value_sum/len(copy_list))
     
    return mittelwert, value_list


# Baut das JSON für die AHT Messwerte zusammen
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


# Überscheibt den Display Bereich der Boot Message
def clear_boot():
    tft.fill_rect(0,105,320,25, st7789.BLACK) #x,y,width,height
    

# Schreibt die Boot Logs aufs Display
def log_display(text):
    
    tft.text(font, CLEAR , START_TEXT, 90, st7789.WHITE, st7789.BLACK)
    tft.text(font, "- LOG -" , 100, 90, st7789.WHITE, st7789.BLACK)    
    
    tft.text(font, CLEAR , START_TEXT, 120, st7789.WHITE, st7789.BLACK)
    tft.text(font, text , START_TEXT, 120, st7789.WHITE, st7789.BLACK)
    

# Schaltet das Display Statusabhänig ein und aus  
def show_display(pin=0): # Pin =0 hat vordefiniert werte, um die Funktion außerhalb des interrupt verwenden zu können
    
    global display_state
    global display_activation_time
    global display_on_timestamp_ms
    
    time = utime.ticks_ms()
    
    # Entprellung, dass das Display nur alle 3s neu aktiviert werden kann
    if time - display_activation_time >= 3000:
        
        if tft.backlight.value() == 0:
            
            display_state = True
            print(display_state)
            print("Display on")
            
            display_activation_time = utime.ticks_ms()
            display_on_timestamp_ms = utime.ticks_ms()
            
        else:
            display_activation_time = utime.ticks_ms()
            display_off()

# Schaltet das Display aus. Ausgelagert, da er an mehreren Stellen benötigt wird, unabhänig von show_display()
def display_off():
    
    global display_state
    
    display_state = False
    tft.backlight.value(0)
    tft.fill(st7789.BLACK)
    tft.sleep_mode(True)
    print("Display off")


# Einheitliche Funktion um genaue Zeitstempel zu generieren
def timestamp_generator():
    clock = utime.localtime()
    timestamp = f"{clock[0]}-{clock[1]}-{clock[2]}T{clock[3]}:{clock[4]}:{clock[5]}_MEZ"
    
    return timestamp


# Baut JSON zum ablegen der Logs in einer Datenbank zusammen
def log(eventtype, log_message):
    
    global MQTT_TOPIC_LOG
    
    json_raw = {
            "eventtype" : eventtype,
            "event_text" : log_message
            }
    
    json_data = ujson.dumps(json_raw)
    
    mqtt_publish(json_data, MQTT_TOPIC_LOG)
    

#---------------- Funktion WIFI -------------------------------------------

# Stellt eine W-Lan Verbindung her
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
taster_schuko12.irq(trigger = Pin.IRQ_RISING, handler = schuko12_irq)
taster_schuko34.irq(trigger = Pin.IRQ_RISING, handler = schuko34_irq)


#---------------- Boot Display --------------------------------------------

# Visualisierung einer kurzen bootsequenz auf dem Display
tft.backlight.value(1)
tft.fill(st7789.BLACK)

tft.text(font, SNOWFLAKE , 20, 30, st7789.WHITE, st7789.BLACK)
tft.text(font, BOOT , 35, 110, st7789.WHITE, st7789.BLACK)
tft.text(font, SNOWFLAKE , 20, 190, st7789.WHITE, st7789.BLACK)

utime.sleep(1)
clear_boot()


# -------- MQTT-Client erzeugen, Callback festlegen und Topic abonnieren --
   
connectWIFI()

mqtt_shelly = MQTTClient(CLIENT_ID_shelly, MQTT_SERVER)
mqtt_shelly.set_callback(sub_shelly) 
utime.sleep(1) 
mqtt_shelly.connect() 
mqtt_shelly.subscribe(MQTT_TOPIC_shelly_energy)

log_display("- MQTT shelly")
log("MQTT_Master", "shelly verbunden")
print("MQTT_Master shelly verbunden!")

utime.sleep(1)

display_off()

log("Systemstatus", "Master Controller online, start loop")

#---------------- Hauptprogramm ------------------------------------------- 
while True:
    cycle_time_ms = utime.ticks_ms() # Zykluszeit
    
    if cycle_time_ms - last_shelly_check_ms > INTERVALL_MS_SHELLY_ENERGY: # reduziert Broker verbindunden und spart Energie. Shelly sendet im Intervall von ~10s Daten
        try:
            mqtt_shelly.check_msg()
            last_shelly_check_ms = utime.ticks_ms()
        
        except Exception as e:
            log("Master mqtt_shelly check error", e)
            
        utime.sleep(1)


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
        log("Master AHT error", e)
        
#---------------- Display einschalten -------------------------------------
    try:
        # Wird nur im angegeben Intervall von INTERVALL_MS_DISPLAY_UPDATE aufgeruden,sofern das Display eingschaltet sein soll
        if display_state == True and (cycle_time_ms - display_update_time) >= INTERVALL_MS_DISPLAY_UPDATE:
            
            if cycle_time_ms - display_on_timestamp_ms <= DISPLAY_SHUTDOWN_TIME_MS: # automatische Abschaltung nach 3 Minuten (Änderungsparameter: DISPLAY_SHUTDOWN_TIME_MS)
            
                initial_run = False
                
                # Wird nur im ersten Durchlauf aufgerufen
                if tft.backlight.value() == 0:
                    display_on_timestamp_ms = utime.ticks_ms()
                
                    # Display einschalten
                    tft.sleep_mode(False)
                    tft.backlight.value(1)
                    
                    # Messwerte für den ersten durchlauf setzten, um später displayaktualisierungen zu minimieren
                    initial_run = True 
                    
                
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
                print("else off")
                display_off() 
        
    except Exception as e:
        log(" Master Display error", e)
