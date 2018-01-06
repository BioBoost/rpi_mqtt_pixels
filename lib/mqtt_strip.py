from lib.simple_mqtt_client import *
from lib.effects.color_effect import *
from lib.effects.nightrider_effect import *
from lib.effects.rainbow_effect import *
from lib.effects.strobe_effect import *
from lib.effects.group_shift_effect import *
from lib.effect_manager import *
from uuid import getnode as get_mac
import json
from jsonschema import validate
from jsonschema import exceptions

neopixel_schema = {
    "type" : "object",
    "properties" : {
        "state" : {"enum" : ["ON", "OFF"]},
        "effect" : {"enum" : ["rainbow", "nightrider", "strobe", "groupshift"]},
        "interval_ms" : {"type": "number", "minimum": 0, "maximum": 5000 },
        "group_size" : {"type": "number"},
        "brightness" : {"type": "number", "minimum": 0, "maximum": 255 },
        "color": {
            "type" : "object",
            "properties" : {
                "r" : {"type": "number", "minimum": 0, "maximum": 255 },
                "g" : {"type": "number", "minimum": 0, "maximum": 255 },
                "b" : {"type": "number", "minimum": 0, "maximum": 255 }
            },
            "required": ["r", "g", "b"]
        }
    }
}

class MqttStrip(object):
    def __init__(self, pixelStrip, mqttBroker, baseTopic, stripId="neopixels", retainEffect=False):
        self.pixelStrip = pixelStrip
        self.mqttBroker = mqttBroker
        self.baseTopic = baseTopic
        self.stripId = stripId
        self.retainEffect = retainEffect
        self.effectManager = EffectManager(pixelStrip)
        self.effectManager.set_effect(ColorEffect(pixelStrip, Colors.BLACK))
        self.effectManager.disable()
        self.__setup_mqtt()

    def stop(self):
        print("Stopping MQTT Strip API")
        self.mqttClient.stop()
        self.pixelStrip.off()

    def __setup_mqtt(self):
        clientId = str(get_mac()) + "-python_client"
        self.mqttClient = SimpleMqttClient(clientId, self.mqttBroker)
        self.mqttClient.subscribe(self.baseTopic + "/" + self.stripId + "/set", self.__mqtt_message_handler)
        sleep(2)
        self.__publish_pixel_strip_state()       # For Home Assistant

    def __mqtt_message_handler(self, client, userdata, msg):
        print("Getting set pixel strip request: " + msg.payload.decode('utf-8'))
        self.__set_pixel_strip(msg.payload.decode('utf-8'))
        self.__publish_pixel_strip_state()       # For Home Assistant

    def __set_pixel_strip(self, jsonString):
        try:
            jsonData = json.loads(jsonString)
            # If no exception is raised by validate(), the instance is valid.
            validate(jsonData, neopixel_schema)

            if 'state' in jsonData:
                if jsonData['state'] == 'ON':
                    self.effectManager.enable()
                elif jsonData['state'] == 'OFF':
                    self.effectManager.disable()

            if len(jsonData.keys()) > 1:
                effect = ColorEffect(self.pixelStrip)
                if self.retainEffect:
                    effect = self.effectManager.get_current_effect()

                if ('effect' in jsonData) and (jsonData['effect'] == 'nightrider'):
                    effect = NightRiderEffect(self.pixelStrip)
                elif ('effect' in jsonData) and (jsonData['effect'] == 'rainbow'):
                    effect = RainbowEffect(self.pixelStrip)
                elif ('effect' in jsonData) and (jsonData['effect'] == 'strobe'):
                    effect = StrobeEffect(self.pixelStrip)
                elif ('effect' in jsonData) and (jsonData['effect'] == 'groupshift'):
                    effect = GroupShiftEffect(self.pixelStrip)
                    groupSize = jsonData['group_size'] if ('group_size' in jsonData) else 8
                    effect.set_group_size(groupSize)

                if 'color' in jsonData:
                    components = jsonData['color']
                    effect.set_color(Color(components['r'], components['g'], components['b']))

                if ('brightness' in jsonData):
                    effect.set_brightness(jsonData['brightness'])

                if ('interval_ms' in jsonData):
                    effect.set_update_interval(jsonData['interval_ms']/1000)

                self.effectManager.set_effect(effect)

        except exceptions.ValidationError:
            print("Message failed validation")
        except ValueError:
            print("Invalid json string")

    def __publish_pixel_strip_state(self):
        state = self.__get_pixel_strip_state()
        (status, mid) = self.mqttClient.publish(self.baseTopic + "/" + self.stripId, state)
        if status != 0:
            print("Could not send state")

    def __get_pixel_strip_state(self):
        json_state = {
            "brightness": self.effectManager.get_current_effect().get_brightness(),
            "state": "ON" if self.effectManager.is_enabled() else "OFF",
            "color": {
                "r": self.effectManager.get_current_effect().get_color().red(),
                "g": self.effectManager.get_current_effect().get_color().green(),
                "b": self.effectManager.get_current_effect().get_color().blue()
            }
        }

        if isinstance(self.effectManager.get_current_effect(), NightRiderEffect):
            json_state['effect'] = 'nightrider'
        elif isinstance(self.effectManager.get_current_effect(), RainbowEffect):
            json_state['effect'] = 'rainbow'
        elif isinstance(self.effectManager.get_current_effect(), StrobeEffect):
            json_state['effect'] = 'strobe'
        elif isinstance(self.effectManager.get_current_effect(), GroupShiftEffect):
            json_state['effect'] = 'groupshift'

        return json.dumps(json_state)
