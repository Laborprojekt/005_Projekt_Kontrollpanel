'''
Name:           Kontrollpanel
Datum:          05.05.2025
Version:        1.0

Entwickler:     Eberlei

Hardware:
- ESP32-S3-DevKitC-1
- SRD-03VDC-SL-C (NC)
- SRD-03VDC-SL-C (NO)
'''

from machine import Pin, SoftI2C
import utime
import ujson
import network
from umqtt.simple import MQTTClient


#---------------- Pin ----------------#

rl_reboot = Pin(14,Pin.OUT)    #NC
rl_schuko_1 = Pin(13, Pin.OUT) #NO
rl_schuko_2 = Pin(12, Pin.OUT) #NO
rl_schuko_3 = Pin(11, Pin.OUT) #NO
rl_schuko_4 = Pin(10, Pin.OUT) #NO
rl_schuko_5 = Pin(9, Pin.OUT) #NO


#---------------- Variablen / Konstanten ----------------#

# Allgemein
cycle_time_ms = 0


# Variablen Steckdose
reboot = False
schuko12 = False
schuko34 = False

schuko1 = False
schuko2 = False
schuko3 = False
schuko4 = False


#---------------- MQTT-Konfiguration ----------------#
CLIENT_ID_relais = "ESP_Relais_Sub"
CLIENT_ID_ESP = "ESP_send_Sub"
MQTT_TOPIC_relais = "node-red_relais_button"
MQTT_TOPIC_LOG = "ESP_logs"

# @home
WIFI_SSID = "502-Bad-Gateway"
WIFI_PASSWORD = "66813838796323588312"
MQTT_SERVER = "192.168.188.26"   #Achtung: aktuelle Adresse des Brokers!

# @BZTG
#WIFI_SSID = "BZTG-IoT" 
#WIFI_PASSWORD = "WerderBremen24"
#MQTT_SERVER = "192.168.1.195"   #Achtung: aktuelle Adresse des Brokers!

BAUGRUPPE = "ESP_Sub" # Info für JSON

#---------------- Funktion zur Datenauswertung -------------

# Liest die Schaltbefehle auf dem Node-Red UI aus und setzt die Schaltparameter für die Hauptsschleife
def sub_relais(topic, msg):
    global reboot, schuko12, schuko34, schuko1, schuko2, schuko3, schuko4
    
    daten = ujson.loads(msg)
    print("sub_relais")
    
    reboot_value, schuko12_value, schuko34_value, schuko1_value, schuko2_value, schuko3_value, schuko4_value = 0,0,0,0,0,0,0

    try:
        reboot_value = daten.get("reboot")
        group_off_value = daten.get("group_off")
        group_on_value = daten.get("group_on")
        schuko12_value = daten.get("schuko12")
        schuko34_value = daten.get("schuko34")
        schuko1_value = daten.get("schuko1")
        schuko2_value = daten.get("schuko2")
        schuko3_value = daten.get("schuko3")
        schuko4_value = daten.get("schuko4")
        group_on_value = daten.get("group_on")
        print(reboot_value, group_off_value, group_on_value, schuko12_value, schuko34_value, schuko1_value, schuko2_value, schuko3_value, schuko4_value)

    except:
        pass
  
    # Setzt bei Bedarf die Variablen der Relais
    if reboot_value:
        reboot = not reboot
        
    if group_off_value:
        schuko12 = False
        schuko34 = False
        schuko1 = False
        schuko2 = False
        schuko3 = False
        schuko4 = False
    
    if group_on_value:
        schuko12 = True
        schuko34 = True
        schuko1 = True
        schuko2 = True
        schuko3 = True
        schuko4 = True
    
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


# -------- MQTT-Client erzeugen, Callback festlegen und Topic abonnieren --
   
connectWIFI()

mqtt_relais = MQTTClient(CLIENT_ID_relais, MQTT_SERVER)
mqtt_relais.set_callback(sub_relais) 
utime.sleep(1) 
mqtt_relais.connect() 
mqtt_relais.subscribe(MQTT_TOPIC_relais)
log("MQTT_Sub", "relais verbunden")
print("MQTT relais verbunden!")


log("Systemstatus", "SUB Controller online, start loop")

#---------------- Hauptprogramm ------------------------------------------- 
while True:
    cycle_time_ms = utime.ticks_ms() # Zykluszeit
    
    try:
        mqtt_relais.check_msg()
    
    except Exception as e:
        log("Sub mqtt_relais check error", e)
        
    utime.sleep(1)

#---------------- Relais schalten ----------------------------------------- 
    rl_reboot.value(reboot)
    rl_schuko_1.value(schuko1)
    rl_schuko_2.value(schuko2)
    rl_schuko_3.value(schuko3)
    rl_schuko_4.value(schuko4)
