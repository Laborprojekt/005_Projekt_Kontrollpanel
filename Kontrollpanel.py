'''
Name:           Kontrollpanel
Datum:          16.03.2025
Version:        1.0

Entwickler:     Eberlei

Hardware:
- ESP32-S3-DevKitC-1
- SRD-03VDC-SL-C (NC)
- SRD-03VDC-SL-C (NO)
- AHT20
- Shelly plus 1 PM
'''

from machine import Pin
import utime
import ujson
import network
from umqtt.simple import MQTTClient

#---------------- Pin ----------------#

rl_reboot = Pin(9,Pin.OUT)    #NC
rl_schuko_1 = Pin(10, Pin.OUT) #NO
rl_schuko_2 = Pin(11, Pin.OUT) #NO
rl_schuko_3 = Pin(12, Pin.OUT) #NO
rl_schuko_4 = Pin(13, Pin.OUT) #NO


#---------------- Variablen ----------------#

reboot = False
schuko12 = False
schuko34 = False

schuko1 = False
schuko2 = False
schuko3 = False
schuko4 = False

shelly_energy = {}

#---------------- MQTT-Konfiguration ----------------#
MQTT_SERVER = "192.168.1.147"   #Achtung: aktuelle Adresse des Brokers! 
CLIENT_ID_relais = "ESP_Relais"
CLIENT_ID_shelly = "ESP_Shelly"
MQTT_TOPIC_relais = "dashboard_switch"
MQTT_TOPIC_shelly = "shelly"
WIFI_SSID = "BZTG-IoT" 
WIFI_PASSWORD = "WerderBremen24"

#---------------- Funktion zur Datenauswertung ------------- 
def sub_relais(topic, msg):  
    daten = ujson.loads(msg)
    print("sub_relais")
    
    reboot_value, schuko12_value, schuko34_value, schuko1_value, schuko2_value, schuko3_value, schuko4_value = 0,0,0,0,0,0,0
    '''
    schuko12_value = 0
    schuko34_value = 0
    schuko1_value = 0
    schuko2_value = 0
    schuko3_value = 0
    schuko4_value = 0
    '''
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
    '''
    try:
        schuko12_value = daten.get("schuko12")
        print(schuko12_value)
    except:
        pass
    
    try:
        schuko34_value = daten.get("schuko34")
        print(schuko34_value)
    except:
        pass
    '''   
    
    global reboot, schuko12, schuko34, schuko1, schuko2, schuko3, schuko4
    
    if reboot_value:
        reboot = not reboot
    
    if schuko12_value:
        schuko12 = not schuko12
        
    if schuko34_value:
        schuko34 = not schuko34
         
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
    
    
# ------------------------------ Funktion WIFI ------------- 
def connectWIFI(): 
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True) 
    wlan.connect(WIFI_SSID, WIFI_PASSWORD) 
    while not wlan.isconnected(): 
        pass 
    print ("wifi connected")   
    print(wlan.ifconfig()) # WIFI verbinden   

#-------- MQTT-Client erzeugen, Callback festlegen und Topic abonnieren --
    
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

#---------------- pwm aufgrund des Inhalts von pwm_duty schalten ------------ 
    rl_reboot.value(reboot)
    rl_schuko_1.value(schuko1)
    rl_schuko_2.value(schuko2)
    rl_schuko_3.value(schuko3)
    rl_schuko_4.value(schuko4)
    
    if schuko12 or rl_schuko_1.value() and rl_schuko_2.value() == False:
        rl_schuko_1.value(schuko12)
        rl_schuko_2.value(schuko12)
        
    if schuko34 or schuko3 and schuko4 == False:
        rl_schuko_3.value(schuko34)
        rl_schuko_4.value(schuko34)

