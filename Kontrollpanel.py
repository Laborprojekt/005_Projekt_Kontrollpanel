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


#---------------- Variablen ----------------#

reboot = False
schuko12 = False
shelly_energy = {}

#---------------- MQTT-Konfiguration ----------------#
MQTT_SERVER = "192.168.1.205"   #Achtung: aktuelle Adresse des Brokers! 
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
    try:
        reboot_value = daten.get('reboot')
        print(reboot_value)
    except:
        pass
    
    try:
        schuko12_value = daten.get("schuko12")
        print(schuko12_value)
    except:
        pass
    
    
    global reboot, schuko12
    reboot = reboot_value
    schuko12 = schuko12_value
    
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
    rl_schuko_1.value(schuko12)

