############  INSTALAR ##############
# paho-mqtt, version 1.6.1
#####################################

import paho.mqtt.client as mqtt
import json
from dronLink.Dron import Dron
import random as r

# esta función sirve para publicar los eventos resultantes de las acciones solicitadas
def publish_event (event):
    global sending_topic, client
    client.publish(sending_topic + '/'+event)


def publish_telemetry_info (telemetry_info):
    # cuando reciba datos de telemetría los publico
    global sending_topic, client
    #print(f'Publicacion reciente {telemetry_info}')
    client.publish(sending_topic + '/telemetryInfo', json.dumps(telemetry_info))

def on_message(cli, userdata, message):
    global  sending_topic, client
    global dron
    # el mensaje que se recibe tiene este formato:
    #    "origen"/autopilotServiceDemo/"command"
    # tengo que averiguar el origen y el command
    splited = message.topic.split("/")
    origin = splited[0] # aqui tengo el nombre de la aplicación que origina la petición
    command = splited[2] # aqui tengo el comando

    sending_topic = "G3/autopilotServiceDemo/" + origin # lo necesitaré para enviar las respuestas
    print(splited)
    
    if command == 'connect':
        connection_string = 'tcp:127.0.0.1:5763'
        baud = 115200
        dron.connect(connection_string, baud, freq=10)
        publish_event('connected')

    if command == 'arm_takeOff':
        if dron.state == 'connected':
            print ('vamos a armar')
            dron.arm()
            print ('vamos a despegar')
            dron.takeOff(float(splited[3]) if len(splited) > 3 else 5, blocking=False, callback=publish_event, params='flying')

    if command == 'go':
        if dron.state == 'flying':
            #direction = message.payload.decode("utf-8")
            dron.go(splited[3])

    if command == 'Land':
        if dron.state == 'flying':
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.Land(blocking=False, callback=publish_event, params='landed')

    if command == 'RTL':
        if dron.state == 'flying':
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.RTL(blocking=False, callback=publish_event, params='atHome')

    if command == 'startTelemetry':
        # indico qué función va a procesar los datos de telemetría cuando se reciban
        dron.send_telemetry_info(publish_telemetry_info)

    if command == 'stopTelemetry':
        dron.stop_sending_telemetry_info()

    if command == 'changeSpeed':
        if dron.state == 'flying':
            dron.changeNavSpeed(float(splited[3]))
    
    if command == 'changeHeading':
        if dron.state == 'flying':
            dron.changeHeading(float(splited[3]))


def on_connect(client, userdata, flags, rc):
    global connected
    if rc==0:
        print("connected OK Returned code=",rc)
        connected = True
    else:
        print("Bad connection Returned code=",rc)


dron = Dron()

client = mqtt.Client(str(r.randint(100,999))+"autopilotServiceDemo", transport="websockets")

# me conecto al broker publico y gratuito
broker_address = "broker.hivemq.com"
broker_port = 8000

client.on_message = on_message
client.on_connect = on_connect
client.connect (broker_address,broker_port)

# me subscribo a todos los mensajes cuyo destino sea este servicio
client.subscribe('+/autopilotServiceDemo/#')
print ('AutopilotServiceDemo esperando peticiones')
client.loop_forever()

