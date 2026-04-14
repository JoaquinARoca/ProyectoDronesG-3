####### INSTALAR ###############
# ultralytics
# torch
# seaborn
# tpdm
#######################################

import threading
import tkinter as tk
from dronLink.Dron import Dron

import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import torch


class Detector:
    def __init__ (self):
        # Cargar el modelo YOLOv5 preentrenado de Ultralytics
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.model.eval()

        # Inicializar la captura de video desde webcam (índice 0) o usa un archivo con 'video.mp4'
        self.cap = cv2.VideoCapture(0)

    def detect (self, frame, objectID):
        # Convertir frame a RGB para YOLO
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Inferencia con el modelo
        results = self.model(img_rgb)
        detectado = False
        # Procesar resultados

        for *box, conf, cls in results.xyxy[0]:
            if int(cls.item()) == objectID:
                x1, y1, x2, y2 = map(int, box)
                detectado = True
        if detectado:
            return True,  [x1, y1, x2, y2]
        else:
            return False, None


class VideoReceiver:
    def __init__(self):
        self.track = None
        self.detector = Detector()
        self.objectID = None

    def setObject (self, objectID):
        self.objectID = objectID

    async def handle_track(self, track):
        print("Inside handle track")
        self.track = track
        frame_count = 0
        detectado = False
        while True:
            try:
                #print("Waiting for frame...")
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                frame_count += 1
                #print(f"Received frame {frame_count}")

                if isinstance(frame, VideoFrame):
                    #print(f"Frame type: VideoFrame, pts: {frame.pts}, time_base: {frame.time_base}")
                    frame = frame.to_ndarray(format="bgr24")
                elif isinstance(frame, np.ndarray):
                    print(f"Frame type: numpy array")
                else:
                    #print(f"Unexpected frame type: {type(frame)}")
                    continue
                if self.objectID:
                    if frame_count % 15 == 0:
                        detectado, rectangulo  = self.detector.detect(frame,self.objectID)

                    if detectado:
                        label = "here"
                        x1, y1, x2, y2 = rectangulo
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, label, (x1, y1 - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow("Frame", frame)

                # Exit on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except asyncio.TimeoutError:
                print("Timeout waiting for frame, continuing...")
            except Exception as e:
                print(f"Error in handle_track: {str(e)}")
                if "Connection" in str(e):
                    break
        print("Exiting handle_track")


async def run(pc, signaling):
    await signaling.connect()

    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            print(f"Receiving {track.kind} track")
            asyncio.ensure_future(video_receiver.handle_track(track))

    @pc.on("datachannel")
    def on_datachannel(channel):
        print(f"Data channel established: {channel.label}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state is {pc.connectionState}")
        if pc.connectionState == "connected":
            print("WebRTC connection established successfully")

    print("Waiting for offer from sender...")
    offer = await signaling.receive()
    print("Offer received")
    await pc.setRemoteDescription(offer)
    print("Remote description set")

    answer = await pc.createAnswer()
    print("Answer created")
    await pc.setLocalDescription(answer)
    print("Local description set")

    await signaling.send(pc.localDescription)
    print("Answer sent to sender")

    print("Waiting for connection to be established...")
    while pc.connectionState != "connected":
        await asyncio.sleep(0.1)

    print("Connection established, waiting for frames...")
    await asyncio.sleep(100)  # Wait for 35 seconds to receive frames

    print("Closing connection")


async def videoReceiver():
    # el receptor actua de cliente que debe conectarse al emisor que actua de servidor
    IP_server = "localhost"
    signaling = TcpSocketSignaling(IP_server, 9999)
    pc = RTCPeerConnection()

    global video_receiver
    video_receiver = VideoReceiver()

    try:
        await run(pc, signaling)
    except Exception as e:
        print(f"Error in main: {str(e)}")
    finally:
        print("Closing peer connection")
        await pc.close()





def showTelemetryInfo (telemetry_info):
    global heading, altitude, groundSpeed, state
    global altShowLbl, headingShowLbl, stateShowLbl
    altShowLbl['text'] = round (telemetry_info['alt'],2)
    headingShowLbl['text'] =  round(telemetry_info['heading'],2)
    stateShowLbl['text'] = telemetry_info['state']


def connect ():
    global dron, speedSldr
    connection_string ='tcp:127.0.0.1:5763'
    baud = 115200
    dron.connect(connection_string,baud)
    # cambiamos el color del boton
    connectBtn['text'] = 'Conectado'
    connectBtn['fg'] = 'white'
    connectBtn['bg'] = 'green'
    # fijamos la velocidad por defecto en el slider
    speedSldr.set(1)

def arm ():
    global dron
    dron.arm()
    armBtn['text'] = 'Armado'
    armBtn['fg'] = 'white'
    armBtn['bg'] = 'green'

def inTheAir ():
    # ya ha alcanzado la altura de despegue
    takeOffBtn['text'] = 'En el aire'
    takeOffBtn['fg'] = 'white'
    takeOffBtn['bg'] = 'green'


def takeoff ():
    global dron
    # despegamos a una altura de 5 metros
    # llamada no bloqueante. Cuando alcance la altura indicada ejecutará la función inTheAir
    dron.takeOff (5, blocking = False,  callback = inTheAir)
    takeOffBtn['text'] = 'Despegando...'
    takeOffBtn['fg'] = 'black'
    takeOffBtn['bg'] = 'yellow'

def land ():
    global dron
    # llamada no bloqueante. El parámetro nos permitirá saber en onEarth que venimos de Land
    dron.Land()
    landBtn['text'] = 'En tierra'
    landBtn['fg'] = 'white'
    landBtn['bg'] = 'green'

def RTL():
    global dron
    # llamada no bloqueante. El parámetro nos permitirá saber en onEarth que venimos de RTL
    dron.RTL()
    RTLBtn['text'] = 'En tierra'
    RTLBtn['fg'] = 'white'
    RTLBtn['bg'] = 'green'

def go (direction, btn):
    global dron, previousBtn
    # cambio el color del anterior boton clicado (si lo hay)
    if previousBtn:
        previousBtn['fg'] = 'black'
        previousBtn['bg'] = 'dark orange'

    # navegamos en la dirección indicada
    dron.go (direction)
    # pongo en verde el boton clicado
    btn['fg'] = 'white'
    btn['bg'] = 'green'
    # tomo nota de que este es el último botón clicado
    previousBtn = btn


def startTelem():
    global dron
    # pedimos datos de telemetría que se procesarán en showTelemetryInfo a medida que vayan llegando
    dron.send_telemetry_info(showTelemetryInfo)

def stopTelem():
    global dron
    dron.stop_sending_telemetry_info()

def changeHeading (event):
    global dron
    global gradesSldr
    # cambiamos el heading según se haya seleccionado en el slider
    dron.changeHeading(int (gradesSldr.get()))

def changeNavSpeed (event):
    global dron
    global speedSldr
    # cambiamos la velocidad de navagación según se haya seleccionado en el slider
    dron.changeNavSpeed(float (speedSldr.get()))

def videoThread ():
    asyncio.run(videoReceiver())

def video ():
    threading.Thread (target = videoThread).start()

def platano ():
    global video_receiver
    video_receiver.setObject(46)

def clock ():
    video_receiver.setObject(74)

def pizza ():
    video_receiver.setObject(53)

def avion ():
    video_receiver.setObject(4)

def coche ():
    video_receiver.setObject(2)

def moto ():
    video_receiver.setObject(3)

def crear_ventana():
    global dron

    global  altShowLbl, headingShowLbl,  speedSldr, gradesSldr, stateShowLbl
    global connectBtn, armBtn, takeOffBtn, landBtn, RTLBtn
    global previousBtn # aqui guardaré el ultimo boton de navegación clicado

    dron = Dron()

    previousBtn = None

    ventana = tk.Tk()
    ventana.title("Dashboard con conexión directa")
    # la interfaz tiene 10 filas y dos columnas
    ventana.rowconfigure(0, weight=1)
    ventana.rowconfigure(1, weight=1)
    ventana.rowconfigure(2, weight=1)
    ventana.rowconfigure(3, weight=1)
    ventana.rowconfigure(4, weight=1)
    ventana.rowconfigure(5, weight=1)
    ventana.rowconfigure(6, weight=1)
    ventana.rowconfigure(7, weight=1)
    ventana.rowconfigure(8, weight=1)
    ventana.rowconfigure(9, weight=1)
    ventana.columnconfigure(0, weight=1)
    ventana.columnconfigure(1, weight=1)

    # Disponemos los botones, indicando qué función ejecutar cuando se clica cada uno de ellos
    # Los tres primeros ocupan las dos columnas de la fila en la que se colocan
    connectBtn = tk.Button(ventana, text="Conectar", bg="dark orange", command = connect)
    connectBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    armBtn = tk.Button(ventana, text="Armar", bg="dark orange", command=arm)
    armBtn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    takeOffBtn = tk.Button(ventana, text="Despegar", bg="dark orange", command=takeoff)
    takeOffBtn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Slider para seleccionar el heading
    gradesSldr = tk.Scale(ventana, label="Grados:", resolution=5, from_=0, to=360, tickinterval=45,
                              orient=tk.HORIZONTAL)
    gradesSldr.grid(row=4, column=0, columnspan=2,padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    gradesSldr.bind("<ButtonRelease-1>", changeHeading)

    # los dos siguientes también están en la misma fila
    landBtn = tk.Button(ventana, text="aterrizar", bg="dark orange", command=land)
    landBtn.grid(row=5, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    RTLBtn = tk.Button(ventana, text="RTL", bg="dark orange", command=RTL)
    RTLBtn.grid(row=5, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # este es el frame para la navegación. Pequeña matriz de 3 x 3 botones
    navFrame = tk.LabelFrame (ventana, text = "Navegación")
    navFrame.grid(row=6, column=0, columnspan = 2, padx=50, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    navFrame.rowconfigure(0, weight=1)
    navFrame.rowconfigure(1, weight=1)
    navFrame.rowconfigure(2, weight=1)
    navFrame.columnconfigure(0, weight=1)
    navFrame.columnconfigure(1, weight=1)
    navFrame.columnconfigure(2, weight=1)

    # al clicar en cualquiera de los botones se activa la función go a la que se le pasa la dirección
    # en la que hay que navegar y el boton clicado, para que la función le cambie el color
    NWBtn = tk.Button(navFrame, text="NW", bg="dark orange",
                        command= lambda: go("NorthWest", NWBtn))
    NWBtn.grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    NoBtn = tk.Button(navFrame, text="No", bg="dark orange",
                        command= lambda: go("North", NoBtn))
    NoBtn.grid(row=0, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    NEBtn = tk.Button(navFrame, text="NE", bg="dark orange",
                        command= lambda: go("NorthEast", NEBtn))
    NEBtn.grid(row=0, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    WeBtn = tk.Button(navFrame, text="We", bg="dark orange",
                        command=lambda: go("West", WeBtn))
    WeBtn.grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    StopBtn = tk.Button(navFrame, text="St", bg="dark orange",
                        command=lambda: go("Stop", StopBtn))
    StopBtn.grid(row=1, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    EaBtn = tk.Button(navFrame, text="Ea", bg="dark orange",
                        command=lambda: go("East", EaBtn))
    EaBtn.grid(row=1, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)


    SWBtn = tk.Button(navFrame, text="SW", bg="dark orange",
                        #command=lambda: go("SouthWest", SWBtn))
                        command = lambda: go("Down", SWBtn))
    SWBtn.grid(row=2, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    SoBtn = tk.Button(navFrame, text="So", bg="dark orange",
                        command=lambda: go("South", SoBtn))
    SoBtn.grid(row=2, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    SEBtn = tk.Button(navFrame, text="SE", bg="dark orange",
                        #command=lambda: go("SouthEast", SEBtn))
                        command = lambda: go("Up", SEBtn))
    SEBtn.grid(row=2, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)


    # slider para elegir la velocidad de navegación
    speedSldr = tk.Scale(ventana, label="Velocidad (m/s):", resolution=1, from_=0, to=20, tickinterval=5,
                          orient=tk.HORIZONTAL)
    speedSldr.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    speedSldr.bind("<ButtonRelease-1>", changeNavSpeed)

    # botones para pedir/parar datos de telemetría
    StartTelemBtn = tk.Button(ventana, text="Empezar a enviar telemetría", bg="dark orange", command=startTelem)
    StartTelemBtn.grid(row=8, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    StopTelemBtn = tk.Button(ventana, text="Parar de enviar telemetría", bg="dark orange", command=stopTelem)
    StopTelemBtn.grid(row=8, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Este es el frame para mostrar los datos de telemetría
    # Contiene etiquetas para informar de qué datos son y los valores. Solo nos interesan 3 datos de telemetría
    telemetryFrame = tk.LabelFrame(ventana, text="Telemetría")
    telemetryFrame.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky=tk.N + tk.S + tk.E + tk.W)

    telemetryFrame.rowconfigure(0, weight=1)
    telemetryFrame.rowconfigure(1, weight=1)

    telemetryFrame.columnconfigure(0, weight=1)
    telemetryFrame.columnconfigure(1, weight=1)
    telemetryFrame.columnconfigure(2, weight=1)

    # etiquetas informativas
    altLbl = tk.Label(telemetryFrame, text='Altitud')
    altLbl.grid(row=0, column=0,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    headingLbl = tk.Label(telemetryFrame, text='Heading')
    headingLbl.grid(row=0, column=1,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    stateLbl = tk.Label(telemetryFrame, text='Estado')
    stateLbl.grid(row=0, column=2,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # etiquetas para colocar aqui los datos cuando se reciben
    altShowLbl = tk.Label(telemetryFrame, text='')
    altShowLbl.grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    headingShowLbl = tk.Label(telemetryFrame, text='',)
    headingShowLbl.grid(row=1, column=1,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    stateShowLbl = tk.Label(telemetryFrame, text='', )
    stateShowLbl.grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    videoBtn = tk.Button(ventana, text="Recibir video por WebRTC", bg="dark orange", command=video)
    videoBtn.grid(row=10, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    detectFrame = tk.LabelFrame (ventana, text = "Detección de objetos")
    detectFrame.grid(row=11, column=0, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    detectFrame.rowconfigure(0, weight=1)
    detectFrame.columnconfigure(0, weight=1)
    detectFrame.columnconfigure(1, weight=1)
    detectFrame.columnconfigure(2, weight=1)

    bananaBtn = tk.Button(detectFrame, text="Banana", bg="dark orange", command=platano)
    bananaBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    raquetaBtn = tk.Button(detectFrame, text="Reloj", bg="dark orange", command=clock)
    raquetaBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    pizzaBtn = tk.Button(detectFrame, text="Pizza", bg="dark orange", command=pizza)
    pizzaBtn.grid(row=0, column=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Configuramos una fila extra en el frame de detección
    detectFrame.rowconfigure(1, weight=1)

    # Botón avion
    avionBtn = tk.Button(detectFrame, text="Avion", bg="dark orange", command=avion)
    avionBtn.grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Botón Coche
    cocheBtn = tk.Button(detectFrame, text="Coche", bg="dark orange", command=coche)
    cocheBtn.grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Botón Moto
    MotoBtn = tk.Button(detectFrame, text="Moto", bg="dark orange", command=moto)
    MotoBtn.grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
