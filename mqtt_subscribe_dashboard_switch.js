// ########## Aktualisierte Topics 02.05.25 ##########

MQTT.subscribe("node-red_shelly_button", function(topic, message) {
  print("Topic: " + topic);
  print("Message: " + message);

  try {
    let payload = JSON.parse(message);

    if (payload.switch_state === "toggle") {
      Shelly.call("Switch.Toggle", { id: 0 });
    } else {
      print("Unbekannter Befehl: " + payload.switch_state);
    }

  } catch (e) {
    print("Fehler beim Parsen: " + e.message);
  }
});


// ########## ALTE TOPICS ##########

MQTT.subscribe("shelly_switch_dashboard", function(topic, message) {
  print("Topic: " + topic);
  print("Message: " + message);

  try {
    let payload = JSON.parse(message);

    if (payload.switch_state === "ON") {
      Shelly.call("Switch.Set", { id: 0, on: true });
    } else if (payload.switch_state === "OFF") {
      Shelly.call("Switch.Set", { id: 0, on: false });
    } else if (payload.switch_state === "toggle") {
      Shelly.call("Switch.Toggle", { id: 0 });
    } else {
      print("Unbekannter Befehl: " + payload.switch_state);
    }

  } catch (e) {
    print("Fehler beim Parsen: " + e.message);
  }
});