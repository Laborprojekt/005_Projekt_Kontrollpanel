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

from machine import Pin, SoftI2C
import utime
import ujson
import network
from umqtt.simple import MQTTClient
import aht10

#---------------- Pin ----------------#

rl_reboot = Pin(14,Pin.OUT)    #NC
rl_schuko_1 = Pin(13, Pin.OUT) #NO
rl_schuko_2 = Pin(12, Pin.OUT) #NO
rl_schuko_3 = Pin(11, Pin.OUT) #NO
rl_schuko_4 = Pin(10, Pin.OUT) #NO
rl_schuko_5 = Pin(9, Pin.OUT) #NO

schalter_display= Pin (35, Pin.IN, Pin.PULL_DOWN)
taster_schuko12 = Pin(37, Pin.IN, Pin.PULL_DOWN)
taster_schuko34 = Pin(39, Pin.IN, Pin.PULL_DOWN)

i2c = SoftI2C(sda = 41, scl = 42)


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

shelly_energy = {}

# Sensor
aht = aht10.AHT10(i2c = i2c)

# Allgemein
temp_list = []
hum_list = []
last_aht_check = 0
INTERVALL_MS_AHT = 10000

INTERVALL_MS_TASTER = 2000

#---------------- MQTT-Konfiguration ----------------#
MQTT_SERVER = "192.168.188.26"   #Achtung: aktuelle Adresse des Brokers!
CLIENT_ID_relais = "ESP_Relais"
CLIENT_ID_shelly = "ESP_Shelly"
CLIENT_ID_ESP = "ESP_send"
MQTT_TOPIC_relais = "dashboard_switch"
MQTT_TOPIC_shelly = "shelly"
MQTT_TOPIC_AHT = "AHT"

# @home
WIFI_SSID = "502-Bad-Gateway"
WIFI_PASSWORD = "66813838796323588312"

# @BZTG
# WIFI_SSID = "BZTG-IoT" 
# WIFI_PASSWORD = "WerderBremen24"

BAUGRUPPE = "Kontrollpanel"

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
    
    global shelly_energy
    shelly_energy = daten
    
    print(shelly_energy)


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
    
    if timestamp - time_irq_schuko12 >= INTERVALL_MS_TASTER:
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
taster_schuko12.irq(trigger = Pin.IRQ_FALLING, handler = schuko12_irq)
taster_schuko34.irq(trigger = Pin.IRQ_FALLING, handler = schuko34_irq)


# -------- MQTT-Client erzeugen, Callback festlegen und Topic abonnieren --
    
connectWIFI()

mqtt_relais = MQTTClient(CLIENT_ID_relais, MQTT_SERVER)
mqtt_relais.set_callback(sub_relais) 
utime.sleep(1) 
mqtt_relais.connect() 
mqtt_relais.subscribe(MQTT_TOPIC_relais)  
print("MQTT relais verbunden!")

mqtt_shelly = MQTTClient(CLIENT_ID_shelly, MQTT_SERVER)
mqtt_shelly.set_callback(sub_shelly) 
utime.sleep(1) 
mqtt_shelly.connect() 
mqtt_shelly.subscribe(MQTT_TOPIC_shelly)  
print("MQTT shelly verbunden!")


#---------------- Hauptprogramm ------------------------------------------- 
while True: 
    mqtt_relais.check_msg()
    mqtt_shelly.check_msg()
    utime.sleep(1)

#---------------- Relais schalten ----------------------------------------- 
    rl_reboot.value(reboot)
    rl_schuko_1.value(schuko1)
    rl_schuko_2.value(schuko2)
    rl_schuko_3.value(schuko3)
    rl_schuko_4.value(schuko4)

#---------------- Relais schalten -----------------------------------------
    if utime.ticks_ms() - last_aht_check >= INTERVALL_MS_AHT:
        
        last_aht_check = utime.ticks_ms()
        # Messwerte erheben
        temp = aht.temperature()
        hum = aht.humidity()
        
        clock = utime.localtime()
        timestamp = f"{clock[0]}-{clock[1]}-{clock[2]}T{clock[3]}:{clock[4]}:{clock[5]}_MEZ"
        
        # Mittelwerte bilden 
        mid_temp, temp_list = mittelwert(temp, temp_list)
        mid_hum, hum_list = mittelwert(hum, hum_list)
        
        json_data = store_data(timestamp, mid_temp, mid_hum)
        
        mqtt_publish(json_data, MQTT_TOPIC_AHT)
        print("AHT data send")
     

