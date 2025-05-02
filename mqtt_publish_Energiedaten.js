########## Aktualisierte Topics 02.05.25 ##########

let mqtt_topic = "shelly_energydata";


MQTT.publish("shelly", JSON.stringify("hello world!"), 0, false);

// Funktion zum Abrufen und Senden der Messwerte
function sendData() {
    Timer.set(10000,true, function(){
    print("Daten werden abgefragt...");

    Shelly.call("Shelly.GetDeviceInfo", {}, function(deviceInfo, error0) {
        if (error0) {
            print("Fehler bei Shelly.GetDeviceInfo:", JSON.stringify(error0));
            return;
        };
        print("Geräteinformationen empfangen:", JSON.stringify(deviceInfo));

        Shelly.call("Switch.GetStatus", {id: 0}, function(switchStatus, error1) {
            if (error1) {
                print("Fehler bei Switch.GetStatus:", JSON.stringify(error1));
                return;
            };
            print("Switch-Status empfangen:", JSON.stringify(switchStatus));

            Shelly.call("Switch.GetStatus", {id: 0}, function(powerStatus, error2) {
                if (error2) {
                    print("Fehler bei Switch.GetStatus (Strommessung):", JSON.stringify(error2));
                    return;
                };
                print("Energiedaten empfangen:", JSON.stringify(powerStatus));

                // MQTT-Payload erstellen
                let payload = {
                    device_id: deviceInfo.id,
                    mac: deviceInfo.mac,
                    model: deviceInfo.model, 
                    power: powerStatus.apower,  // Leistung (Watt)
                    voltage: powerStatus.voltage,  // Spannung (Volt)
                    current: powerStatus.current,  // Strom (Ampere)
                    energy: powerStatus.aenergy.total,  // Gesamtverbrauch (Wh)
                    temp: powerStatus.temperature.tC, // Temperatur des Moduls in Celsius
                    switch_state: powerStatus.output // Schaltzustand des Relais
                };

                // Prüfen, ob MQTT verbunden ist
                if (MQTT.isConnected()) {
                    MQTT.publish(mqtt_topic, JSON.stringify(payload), 0, false);
                    print("Daten an MQTT gesendet:", JSON.stringify(payload));
                }
                else {
                    print("MQTT nicht verbunden. Daten konnten nicht gesendet werden.");
                }
            });
        });
    });
  });
};

sendData();
########## ALTE TOPICS ##########


let mqtt_topic = "shelly";


MQTT.publish("shelly", JSON.stringify("hello world!"), 0, false);

// Funktion zum Abrufen und Senden der Messwerte
function sendData() {
    Timer.set(10000,true, function(){
    print("Daten werden abgefragt...");

    Shelly.call("Shelly.GetDeviceInfo", {}, function(deviceInfo, error0) {
        if (error0) {
            print("Fehler bei Shelly.GetDeviceInfo:", JSON.stringify(error0));
            return;
        };
        print("Geräteinformationen empfangen:", JSON.stringify(deviceInfo));

        Shelly.call("Switch.GetStatus", {id: 0}, function(switchStatus, error1) {
            if (error1) {
                print("Fehler bei Switch.GetStatus:", JSON.stringify(error1));
                return;
            };
            print("Switch-Status empfangen:", JSON.stringify(switchStatus));

            Shelly.call("Switch.GetStatus", {id: 0}, function(powerStatus, error2) {
                if (error2) {
                    print("Fehler bei Switch.GetStatus (Strommessung):", JSON.stringify(error2));
                    return;
                };
                print("Energiedaten empfangen:", JSON.stringify(powerStatus));

                // MQTT-Payload erstellen
                let payload = {
                    device_id: deviceInfo.id,
                    mac: deviceInfo.mac,
                    model: deviceInfo.model, 
                    power: powerStatus.apower,  // Leistung (Watt)
                    voltage: powerStatus.voltage,  // Spannung (Volt)
                    current: powerStatus.current,  // Strom (Ampere)
                    energy: powerStatus.aenergy.total,  // Gesamtverbrauch (Wh)
                    temp: powerStatus.temperature.tC, // Temperatur des Moduls in Celsius
                    switch_state: powerStatus.output // Schaltzustand des Relais
                };

                // Prüfen, ob MQTT verbunden ist
                if (MQTT.isConnected()) {
                    MQTT.publish(mqtt_topic, JSON.stringify(payload), 0, false);
                    print("Daten an MQTT gesendet:", JSON.stringify(payload));
                }
                else {
                    print("MQTT nicht verbunden. Daten konnten nicht gesendet werden.");
                }
            });
        });
    });
  });
};

sendData();