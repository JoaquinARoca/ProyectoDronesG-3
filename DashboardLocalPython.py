##########  INSTALAR ##########
# pymavlink (opcional)
###############################

import tkinter as tk
from tkinter import simpledialog, messagebox
import time
import math
import os
from dronLink.Dron import Dron
import threading
import asyncio
import cv2
import numpy as np
import subprocess
import sys
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.signaling import TcpSocketSignaling
    from av import VideoFrame
    import torch
    WEBDRTC_AVAILABLE = True
except Exception:
    RTCPeerConnection = None
    RTCSessionDescription = None
    MediaStreamTrack = None
    TcpSocketSignaling = None
    VideoFrame = None
    torch = None
    WEBDRTC_AVAILABLE = False

# Optional map widget
try:
    from tkintermapview import TkinterMapView
    MAP_AVAILABLE = True
except Exception:
    TkinterMapView = None
    MAP_AVAILABLE = False


def _do_connect(connection_string, baud):
    """Attempt to connect the drone and update UI; returns True on success."""
    global dron, speedSldr
    try:
        dron.connect(connection_string, baud)
    except Exception as e:
        try:
            messagebox.showerror('Conexión fallida', f'No se pudo conectar a {connection_string} (baud {baud}): {e}')
        except Exception:
            pass
        return False

    try:
        connectBtn['text'] = 'Conectado'
        connectBtn['fg'] = 'white'
        connectBtn['bg'] = 'green'
    except Exception:
        pass
    try:
        speedSldr.set(1)
    except Exception:
        pass
    return True


def connect_auto(mode, com=None):
    """Programmatic connect used when dashboard is started with args from launcher.
    mode: 'sim' or 'esc'. If 'esc', com must be provided like 'COM3'."""
    if mode is None:
        return
    if mode == 'sim':
        connection_string = 'tcp:127.0.0.1:5763'
        baud = 115200
    elif mode == 'esc':
        if not com:
            return
        connection_string = com
        baud = 57600
    else:
        return
    _do_connect(connection_string, baud)

# Globals
map_widget = None
drone_marker = None
heading_line = None
path_segments = []  # list of map path objects for fading trail
path_points = []    # list of (lat, lon, timestamp)
_marker_icon = None
center_enabled = True


# ------------------ Video receive/ detection (copied from DashboardLocalConDeteccion.py) ------------------
####### INSTALAR ###############
# ultralytics
# torch
# seaborn
# tpdm
#######################################

import threading
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
            return True, [x1, y1, x2, y2]
        else:
            return False, None
    


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


# ------------------ Video receive/ detection (copied from DashboardLocalConDeteccion.py) ------------------
class Detector:
    def __init__(self):
        global torch
        self.model = None
        if WEBDRTC_AVAILABLE and torch is not None:
            try:
                # load yolov5s via torch hub (ultralytics)
                self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                self.model.eval()
            except Exception:
                self.model = None

    def detect(self, frame, objectID):
        # Run detection on BGR frame and return True + bbox if objectID detected
        if self.model is None:
            return False, None
        try:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.model(img)
            for *box, conf, cls in results.xyxy[0]:
                if int(cls.item()) == objectID:
                    x1, y1, x2, y2 = map(int, box)
                    return True, [x1, y1, x2, y2]
            return False, None
        except Exception:
            return False, None


class VideoReceiver:
    def __init__(self):
        self.track = None
        self.detector = Detector()
        self.objectID = None

    def setObject(self, objectID):
        self.objectID = objectID

    async def handle_track(self, track):
        print("Inside handle track")
        self.track = track
        frame_count = 0
        detectado = False
        while True:
            try:
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                frame_count += 1
                if isinstance(frame, VideoFrame):
                    frame = frame.to_ndarray(format='bgr24')
                elif isinstance(frame, np.ndarray):
                    pass
                else:
                    continue

                if self.objectID:
                    if frame_count % 15 == 0:
                        detectado, rectangulo = self.detector.detect(frame, self.objectID)
                    if detectado and rectangulo:
                        label = 'here'
                        x1, y1, x2, y2 = rectangulo
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow('Frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except asyncio.TimeoutError:
                print('Timeout waiting for frame, continuing...')
            except Exception as e:
                print(f'Error in handle_track: {e}')
                if 'Connection' in str(e):
                    break
        print('Exiting handle_track')


async def run(pc, signaling):
    await signaling.connect()

    @pc.on('track')
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            print(f'Receiving {track.kind} track')
            asyncio.ensure_future(video_receiver.handle_track(track))

    @pc.on('datachannel')
    def on_datachannel(channel):
        print(f'Data channel established: {channel.label}')

    @pc.on('connectionstatechange')
    async def on_connectionstatechange():
        print(f'Connection state is {pc.connectionState}')
        if pc.connectionState == 'connected':
            print('WebRTC connection established successfully')

    print('Waiting for offer from sender...')
    offer = await signaling.receive()
    print('Offer received')
    await pc.setRemoteDescription(offer)
    print('Remote description set')

    answer = await pc.createAnswer()
    print('Answer created')
    await pc.setLocalDescription(answer)
    print('Local description set')

    await signaling.send(pc.localDescription)
    print('Answer sent to sender')

    print('Waiting for connection to be established...')
    while pc.connectionState != 'connected':
        await asyncio.sleep(0.1)

    print('Connection established, waiting for frames...')
    await asyncio.sleep(100)

    print('Closing connection')


async def videoReceiver():
    IP_server = 'localhost'
    signaling = TcpSocketSignaling(IP_server, 9999)
    pc = RTCPeerConnection()

    global video_receiver
    video_receiver = VideoReceiver()

    try:
        await run(pc, signaling)
    except Exception as e:
        print(f'Error in main: {e}')
    finally:
        print('Closing peer connection')
        await pc.close()


def videoThread():
    asyncio.run(videoReceiver())


def video():
    threading.Thread(target=videoThread).start()


def platano():
    global video_receiver
    if video_receiver:
        video_receiver.setObject(46)


def clock():
    if video_receiver:
        video_receiver.setObject(74)


def pizza():
    if video_receiver:
        video_receiver.setObject(53)


def avion():
    if video_receiver:
        video_receiver.setObject(4)


def coche():
    if video_receiver:
        video_receiver.setObject(2)


def moto():
    if video_receiver:
        video_receiver.setObject(3)
    


def create_fire_circle_icon(size=20):
    """Return a PhotoImage-like object representing a fire-red circle.
    Use Pillow if available for higher quality; otherwise draw into a tk.PhotoImage.
    """
    global Image, ImageDraw, ImageTk
    if 'Image' in globals() and Image is not None:
        try:
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((4, 4, size-5, size-5), fill=(255, 69, 0, 230))
            return ImageTk.PhotoImage(img)
        except Exception:
            pass

    # Fallback: draw circle into a tk.PhotoImage pixel-by-pixel
    img = tk.PhotoImage(width=size, height=size)
    cx = size // 2
    cy = size // 2
    r = (size - 8) // 2
    # Precompute squared radius
    r2 = r * r
    for y in range(size):
        row = []
        dy = y - cy
        for x in range(size):
            dx = x - cx
            if dx*dx + dy*dy <= r2:
                row.append('#FF4500')
            else:
                row.append('')
        # PhotoImage put accepts lists; build a dict of pixels by column range
        # We'll set pixels one by one to ensure compatibility
        for x, color in enumerate(row):
            if color:
                try:
                    img.put(color, (x, y))
                except Exception:
                    pass
    return img


def showTelemetryInfo(telemetry_info):
    """Called periodically with telemetry dict. Updates labels and map marker/path."""
    global map_widget, drone_marker, heading_line, path_points, path_segments, _marker_icon, center_enabled

    try:
        alt = telemetry_info.get('alt')
        heading = telemetry_info.get('heading')
        groundSpeed = telemetry_info.get('groundSpeed')
        state = telemetry_info.get('state')
    except Exception:
        return

    # Update telemetry labels if present
    try:
        altShowLbl['text'] = '' if alt is None else round(alt, 2)
        headingShowLbl['text'] = '' if heading is None else round(heading, 2)
        stateShowLbl['text'] = '' if state is None else state
        speedShowLbl['text'] = '' if groundSpeed is None else round(groundSpeed, 2)
    except Exception:
        pass

    # Update map if available and telemetry contains lat/lon
    if not MAP_AVAILABLE or map_widget is None:
        return

    lat = telemetry_info.get('lat') if isinstance(telemetry_info, dict) else None
    lon = telemetry_info.get('lon') if isinstance(telemetry_info, dict) else None
    if lat is None or lon is None:
        return

    # Create a small fire-red circular icon (cached in _marker_icon) if Pillow is available
    global _marker_icon
    # ensure we have a simple fire-circle icon (cached)
    marker_icon = None
    try:
        if _marker_icon is None:
            _marker_icon = create_fire_circle_icon(size=20)
        marker_icon = _marker_icon
    except Exception:
        marker_icon = None

    # Create or update marker
    try:
        if drone_marker is None:
            if marker_icon is not None:
                try:
                    drone_marker = map_widget.set_marker(lat, lon, text='', icon=marker_icon)
                except Exception:
                    drone_marker = map_widget.set_marker(lat, lon, text='')
                    try:
                        drone_marker.set_icon(marker_icon)
                    except Exception:
                        pass
                _marker_icon = marker_icon
            else:
                drone_marker = map_widget.set_marker(lat, lon, text='')
        else:
            try:
                drone_marker.set_position(lat, lon)
            except Exception:
                try:
                    drone_marker.delete()
                except Exception:
                    pass
                if marker_icon is not None:
                    try:
                        drone_marker = map_widget.set_marker(lat, lon, text='', icon=marker_icon)
                        _marker_icon = marker_icon
                    except Exception:
                        drone_marker = map_widget.set_marker(lat, lon, text='')
                else:
                    drone_marker = map_widget.set_marker(lat, lon, text='')
    except Exception:
        pass

    # Maintain a time-based path of last 5 seconds
    try:
        now = time.time()
        path_points.append((lat, lon, now))
        cutoff = now - 10.0
        path_points = [p for p in path_points if p[2] >= cutoff]
        # remove old segments
        try:
            for s in path_segments:
                try:
                    s.delete()
                except Exception:
                    pass
            path_segments.clear()
        except Exception:
            pass

        # draw segments with fading color
        for i in range(len(path_points)-1):
            (lat1, lon1, t1) = path_points[i]
            (lat2, lon2, t2) = path_points[i+1]
            age = (now - t1) / 5.0
            if age < 0: age = 0
            if age > 1: age = 1
            r1,g1,b1 = (255,140,0)
            r2,g2,b2 = (255,220,180)
            r=int(r1+(r2-r1)*age)
            g=int(g1+(g2-g1)*age)
            b=int(b1+(b2-b1)*age)
            color = '#%02x%02x%02x' % (r,g,b)
            try:
                seg = map_widget.set_path([(lat1, lon1), (lat2, lon2)], color=color, width=3)
            except Exception:
                seg = map_widget.set_path([(lat1, lon1), (lat2, lon2)])
            path_segments.append(seg)
    except Exception:
        pass

    # Draw heading line
    try:
        if heading is not None:
            dist_m = 5.0
            theta = math.radians(float(heading))
            dy = dist_m * math.cos(theta)
            dx = dist_m * math.sin(theta)
            delta_lat = (dy / 111320.0)
            delta_lon = dx / (111320.0 * math.cos(math.radians(lat)) + 1e-12)
            lat2 = lat + delta_lat
            lon2 = lon + delta_lon
            try:
                if heading_line is not None:
                    heading_line.delete()
            except Exception:
                pass
            try:
                heading_line = map_widget.set_path([(lat, lon), (lat2, lon2)], color='#00FF00', width=3)
            except Exception:
                heading_line = None
    except Exception:
        pass

    # Center map if enabled
    try:
        if center_enabled:
            map_widget.set_position(lat, lon)
    except Exception:
        pass


def connect():
    global dron, speedSldr
    try:
        # Ask whether to connect to simulation or to a real scenario (COM)
        respuesta = messagebox.askquestion(
            'Tipo de conexión',
            "¿Conectar a la SIMULACIÓN?\nSí = Simulación (tcp:127.0.0.1:5763, baud 115200)\nNo = Escenario (Puerto COM, baud 57600)"
        )

        if respuesta == 'yes':
            connection_string = 'tcp:127.0.0.1:5763'
            baud = 115200
        else:
            # Ask for COM port. Accept number (e.g. '3') or full name ('COM3' or 'com 3').
            com_input = simpledialog.askstring('Puerto COM', "Introduce el puerto COM (ej. 'COM3' o solo el número '3'):")
            if com_input is None:
                # User cancelled
                return
            com_input = com_input.strip()
            if com_input == '':
                return
            # Normalize: remove spaces and uppercase
            com_norm = com_input.replace(' ', '').upper()
            if com_norm.isdigit():
                connection_string = f'COM{com_norm}'
            elif com_norm.startswith('COM') and com_norm[3:].isdigit():
                connection_string = com_norm
            else:
                # If not valid, inform the user and abort
                messagebox.showerror('Puerto COM inválido', f"Puerto COM inválido: '{com_input}'")
                return
            baud = 57600

        # Try to connect and handle possible failures
        try:
            dron.connect(connection_string, baud)
        except Exception as e:
            messagebox.showerror('Conexión fallida', f'No se pudo conectar a {connection_string} (baud {baud}): {e}')
            return

        connectBtn['text'] = 'Conectado'
        connectBtn['fg'] = 'white'
        connectBtn['bg'] = 'green'
        try:
            speedSldr.set(1)
        except Exception:
            pass
    except Exception as e:
        # unexpected error in UI flow
        try:
            messagebox.showerror('Error', f'Error en proceso de conexión: {e}')
        except Exception:
            pass


def arm():
    global dron
    dron.arm()
    armBtn['text'] = 'Armado'
    armBtn['fg'] = 'white'
    armBtn['bg'] = 'green'


def inTheAir():
    takeOffBtn['text'] = 'En el aire'
    takeOffBtn['fg'] = 'white'
    takeOffBtn['bg'] = 'green'


def takeoff():
    global dron
    altitude = simpledialog.askfloat("Altitud de despegue", "Introduce la altitud en metros:\n(Rango: 1-100m)", minvalue=1.0, maxvalue=100.0)
    if altitude is None:
        return
    try:
        dron.arm()
        armBtn['text'] = 'Armado'
        armBtn['fg'] = 'white'
        armBtn['bg'] = 'green'
    except Exception:
        pass
    try:
        dron.takeOff(int(altitude), blocking=False, callback=inTheAir)
        takeOffBtn['text'] = 'Despegando...'
        takeOffBtn['fg'] = 'black'
        takeOffBtn['bg'] = 'yellow'
    except Exception as e:
        messagebox.showerror('Takeoff fallo', f'No se pudo iniciar el despegue: {e}')


def onLanded():
    landBtn['text'] = 'En tierra'
    landBtn['fg'] = 'white'
    landBtn['bg'] = 'green'


def onRTLCompleted():
    RTLBtn['text'] = 'En tierra'
    RTLBtn['fg'] = 'white'
    RTLBtn['bg'] = 'green'


def land():
    global dron
    dron.Land(blocking=False, callback=onLanded)
    landBtn['text'] = 'Aterrizando...'
    landBtn['fg'] = 'black'
    landBtn['bg'] = 'yellow'


def RTL():
    global dron
    dron.RTL(blocking=False, callback=onRTLCompleted)
    RTLBtn['text'] = 'Volviendo...'
    RTLBtn['fg'] = 'black'
    RTLBtn['bg'] = 'yellow'


def go(direction, btn):
    global dron, previousBtn
    if previousBtn:
        previousBtn['fg'] = 'black'
        previousBtn['bg'] = 'dark orange'
    dron.go(direction)
    btn['fg'] = 'white'
    btn['bg'] = 'green'
    previousBtn = btn


def startTelem():
    global dron
    dron.send_telemetry_info(showTelemetryInfo)


def stopTelem():
    global dron
    dron.stop_sending_telemetry_info()


def changeHeading(event):
    dron.changeHeading(int(gradesSldr.get()))


def changeAltitude(event):
    dron.change_altitude(int(altitudeSldr.get()))


def changeNavSpeed(event):
    dron.changeNavSpeed(float(speedSldr.get()))


def crear_ventana():
    global dron, altShowLbl, headingShowLbl, speedSldr, gradesSldr, stateShowLbl, speedShowLbl, altitudeSldr
    global connectBtn, armBtn, takeOffBtn, landBtn, RTLBtn, previousBtn, map_widget

    dron = Dron()
    previousBtn = None

    ventana = tk.Tk()
    ventana.title('Dashboard con conexión directa')

    # left controls, right map
    left_frame = tk.Frame(ventana, bd=0, relief=tk.FLAT)
    right_frame = tk.Frame(ventana, bd=0, relief=tk.FLAT, width=420, height=640)
    left_frame.grid(row=0, column=0, sticky='nsew')
    right_frame.grid(row=0, column=1, sticky='nsew')
    ventana.columnconfigure(0, weight=3)
    ventana.columnconfigure(1, weight=1)
    ventana.rowconfigure(0, weight=1)

    # Controls
    connectBtn = tk.Button(left_frame, text='Conectar', bg='dark orange', command=connect)
    connectBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    armBtn = tk.Button(left_frame, text='Armar', bg='dark orange', command=arm)
    armBtn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    takeOffBtn = tk.Button(left_frame, text='Despegar', bg='dark orange', command=takeoff)
    takeOffBtn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    def toggle_center():
        global center_enabled
        center_enabled = not center_enabled
        btn_centrar['text'] = 'Centrar: ON' if center_enabled else 'Centrar: OFF'

    btn_centrar = tk.Button(left_frame, text='Centrar: ON', width=12, command=toggle_center)
    btn_centrar.grid(row=2, column=2, padx=5, pady=5)

    # (removed custom image upload UI - marker is a fire-red circle)

    gradesSldr = tk.Scale(left_frame, label='Grados:', resolution=5, from_=0, to=360, orient=tk.HORIZONTAL)
    gradesSldr.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    gradesSldr.set(180)
    gradesSldr.bind('<ButtonRelease-1>', changeHeading)

    altitudeSldr = tk.Scale(left_frame, label='Altitud (m):', resolution=1, from_=0, to=100, orient=tk.HORIZONTAL)
    altitudeSldr.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    altitudeSldr.bind('<ButtonRelease-1>', changeAltitude)

    landBtn = tk.Button(left_frame, text='Aterrizar', bg='dark orange', command=land)
    landBtn.grid(row=5, column=0, padx=5, pady=5, sticky='ew')
    RTLBtn = tk.Button(left_frame, text='RTL', bg='dark orange', command=RTL)
    RTLBtn.grid(row=5, column=1, padx=5, pady=5, sticky='ew')

    navFrame = tk.LabelFrame(left_frame, text='Navegación', bd=0, relief=tk.FLAT)
    navFrame.grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    for r in range(3):
        navFrame.rowconfigure(r, weight=1)
    for c in range(3):
        navFrame.columnconfigure(c, weight=1)

    NWBtn = tk.Button(navFrame, text='NW', bg='dark orange', command=lambda: go('NorthWest', NWBtn))
    NWBtn.grid(row=0, column=0, padx=2, pady=2, sticky='nsew')
    NoBtn = tk.Button(navFrame, text='No', bg='dark orange', command=lambda: go('North', NoBtn))
    NoBtn.grid(row=0, column=1, padx=2, pady=2, sticky='nsew')
    NEBtn = tk.Button(navFrame, text='NE', bg='dark orange', command=lambda: go('NorthEast', NEBtn))
    NEBtn.grid(row=0, column=2, padx=2, pady=2, sticky='nsew')

    WeBtn = tk.Button(navFrame, text='We', bg='dark orange', command=lambda: go('West', WeBtn))
    WeBtn.grid(row=1, column=0, padx=2, pady=2, sticky='nsew')
    StopBtn = tk.Button(navFrame, text='St', bg='dark orange', command=lambda: go('Stop', StopBtn))
    StopBtn.grid(row=1, column=1, padx=2, pady=2, sticky='nsew')
    EaBtn = tk.Button(navFrame, text='Ea', bg='dark orange', command=lambda: go('East', EaBtn))
    EaBtn.grid(row=1, column=2, padx=2, pady=2, sticky='nsew')

    SWBtn = tk.Button(navFrame, text='SW', bg='dark orange', command=lambda: go('Down', SWBtn))
    SWBtn.grid(row=2, column=0, padx=2, pady=2, sticky='nsew')
    SoBtn = tk.Button(navFrame, text='So', bg='dark orange', command=lambda: go('South', SoBtn))
    SoBtn.grid(row=2, column=1, padx=2, pady=2, sticky='nsew')
    SEBtn = tk.Button(navFrame, text='SE', bg='dark orange', command=lambda: go('Up', SEBtn))
    SEBtn.grid(row=2, column=2, padx=2, pady=2, sticky='nsew')

    speedSldr = tk.Scale(left_frame, label='Velocidad (m/s):', resolution=1, from_=0, to=20, orient=tk.HORIZONTAL)
    speedSldr.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    speedSldr.bind('<ButtonRelease-1>', changeNavSpeed)

    StartTelemBtn = tk.Button(left_frame, text='Empezar a enviar telemetría', bg='dark orange', command=startTelem)
    StartTelemBtn.grid(row=8, column=0, padx=5, pady=5, sticky='ew')
    StopTelemBtn = tk.Button(left_frame, text='Parar de enviar telemetría', bg='dark orange', command=stopTelem)
    StopTelemBtn.grid(row=8, column=1, padx=5, pady=5, sticky='ew')

    telemetryFrame = tk.LabelFrame(left_frame, text='Telemetría', bd=0, relief=tk.FLAT)
    telemetryFrame.grid(row=9, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    telemetryFrame.columnconfigure(0, weight=1)
    telemetryFrame.columnconfigure(1, weight=1)
    telemetryFrame.columnconfigure(2, weight=1)
    telemetryFrame.columnconfigure(3, weight=1)

    altLbl = tk.Label(telemetryFrame, text='Altitud')
    altLbl.grid(row=0, column=0, padx=5, pady=5)
    headingLbl = tk.Label(telemetryFrame, text='Heading')
    headingLbl.grid(row=0, column=1, padx=5, pady=5)
    stateLbl = tk.Label(telemetryFrame, text='Estado')
    stateLbl.grid(row=0, column=2, padx=5, pady=5)
    speedLbl = tk.Label(telemetryFrame, text='Velocidad (m/s)')
    speedLbl.grid(row=0, column=3, padx=5, pady=5)

    altShowLbl = tk.Label(telemetryFrame, text='')
    altShowLbl.grid(row=1, column=0, padx=5, pady=5)
    headingShowLbl = tk.Label(telemetryFrame, text='')
    headingShowLbl.grid(row=1, column=1, padx=5, pady=5)
    stateShowLbl = tk.Label(telemetryFrame, text='')
    stateShowLbl.grid(row=1, column=2, padx=5, pady=5)
    speedShowLbl = tk.Label(telemetryFrame, text='')
    speedShowLbl.grid(row=1, column=3, padx=5, pady=5)

    # Video receive button (WebRTC)
    videoBtn = tk.Button(left_frame, text='Recibir video por WebRTC', bg='dark orange', command=lambda: threading.Thread(target=videoThread, daemon=True).start())
    videoBtn.grid(row=10, column=0, columnspan=3, padx=5, pady=5, sticky='ew')


    # Detection buttons (examples)
    detectFrame = tk.LabelFrame(left_frame, text='Detección de objetos')
    detectFrame.grid(row=11, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
    detectFrame.rowconfigure(0, weight=1)
    detectFrame.columnconfigure(0, weight=1)
    detectFrame.columnconfigure(1, weight=1)
    detectFrame.columnconfigure(2, weight=1)

    bananaBtn = tk.Button(detectFrame, text='Banana', bg='dark orange', command=lambda: platano())
    bananaBtn.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
    raquetaBtn = tk.Button(detectFrame, text='Reloj', bg='dark orange', command=lambda: clock())
    raquetaBtn.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
    pizzaBtn = tk.Button(detectFrame, text='Pizza', bg='dark orange', command=lambda: pizza())
    pizzaBtn.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

    # second row of detection buttons
    detectFrame.rowconfigure(1, weight=1)
    avionBtn = tk.Button(detectFrame, text='Avion', bg='dark orange', command=lambda: avion())
    avionBtn.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
    cocheBtn = tk.Button(detectFrame, text='Coche', bg='dark orange', command=lambda: coche())
    cocheBtn.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
    MotoBtn = tk.Button(detectFrame, text='Moto', bg='dark orange', command=lambda: moto())
    MotoBtn.grid(row=1, column=2, padx=5, pady=5, sticky='ew')

    # Initialize map in right_frame
    global map_widget
    if MAP_AVAILABLE:
        try:
            map_widget = TkinterMapView(right_frame, width=420, height=640, corner_radius=0)
            # Default to a detailed Streets style. Prefer Mapbox Streets if token is
            # provided; otherwise use OpenStreetMap standard tiles for clear street detail.
            try:
                mapbox_token = os.environ.get('MAPBOX_TOKEN') or os.environ.get('MAPBOX_API_KEY')
                if mapbox_token:
                    mapbox_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={mapbox_token}'
                    map_widget.set_tile_server(mapbox_url, max_zoom=20)
                else:
                    # use CartoDB Voyager for a more detailed streets style when Mapbox is not available
                    map_widget.set_tile_server('https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', max_zoom=19)
            except Exception:
                try:
                    esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                    map_widget.set_tile_server(esri, max_zoom=19)
                except Exception:
                    pass
            map_widget.pack(fill=tk.BOTH, expand=True)
            map_widget.set_zoom(16)
            # center initially at 0,0
            map_widget.set_position(0, 0)

            # View mode selector: either show Google-like Layers control or directly use Satellite
            viewVar = tk.StringVar(value='Layers')
            # layerVar and change_map_layer implement the Google-like layers menu
            layerVar = tk.StringVar(value='Streets')
            def change_map_layer(selection):
                try:
                    if map_widget:
                        lat, lon = map_widget.get_position()
                        z = map_widget.get_zoom()
                    else:
                        lat = 0; lon = 0; z = 16
                except Exception:
                    lat = 0; lon = 0; z = 16

                sel = selection or layerVar.get()
                # Streets: prefer Mapbox (if token) else CartoDB Voyager for clearer street detail
                mapbox_token = os.environ.get('MAPBOX_TOKEN') or os.environ.get('MAPBOX_API_KEY')
                if mapbox_token:
                    streets_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={mapbox_token}'
                    streets_maxz = 20
                else:
                    streets_url = 'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png'
                    streets_maxz = 19

                candidates = {
                    'Streets': (streets_url, streets_maxz),
                    'Satellite': ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 19),
                }

                try:
                    url, maxz = candidates.get(sel, candidates['Streets'])
                    map_widget.set_tile_server(url, max_zoom=maxz)
                    # restore position/zoom and force a tiny zoom toggle to ensure tile reload
                    try:
                        map_widget.set_zoom(int(z) if isinstance(z, (int, float)) else map_widget.get_zoom())
                        map_widget.set_position(lat, lon)
                        cur_z = int(z) if isinstance(z, (int, float)) else map_widget.get_zoom()
                        tmp_z = cur_z - 1 if cur_z > 0 else cur_z + 1
                        map_widget.set_zoom(tmp_z)
                        def _restore():
                            try:
                                map_widget.set_zoom(cur_z)
                                map_widget.set_position(lat, lon)
                            except Exception:
                                pass
                        map_widget.after(120, _restore)
                    except Exception:
                        try:
                            map_widget.set_zoom(z)
                            map_widget.set_position(lat, lon)
                        except Exception:
                            pass
                except Exception:
                    pass

            # Create a Google-like Layers menubutton (but we'll show/hide it depending on view mode)
            layers_btn = tk.Menubutton(right_frame, text='Layers', bg='white', relief='raised')
            layers_menu = tk.Menu(layers_btn, tearoff=0)
            layers_menu.add_command(label='Streets', command=lambda: change_map_layer('Streets'))
            layers_menu.add_command(label='Satellite', command=lambda: change_map_layer('Satellite'))
            layers_btn.config(menu=layers_menu)

            def change_view_mode(selection):
                # selection is 'Layers' or 'Satellite'
                sel = selection or viewVar.get()
                if sel == 'Satellite':
                    # hide the Layers menubutton and set satellite tiles
                    try:
                        layers_btn.place_forget()
                    except Exception:
                        try:
                            layers_btn.grid_forget()
                        except Exception:
                            pass
                    try:
                        map_widget.set_tile_server('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', max_zoom=19)
                    except Exception:
                        pass
                else:
                    # show Layers menubutton and default to Streets
                    try:
                        layers_btn.place(relx=0.02, rely=0.02)
                    except Exception:
                        try:
                            layers_btn.grid(row=2, column=3, padx=5, pady=5)
                        except Exception:
                            pass
                    # set to Streets by default
                    change_map_layer('Streets')

            # Small OptionMenu in left_frame to toggle between 'Layers' and 'Satellite'
            view_menu = tk.OptionMenu(left_frame, viewVar, 'Layers', 'Satellite', command=change_view_mode)
            view_menu.config(width=12)
            view_menu.grid(row=2, column=3, padx=5, pady=5)
            # ensure Layers menubutton visible initially
            try:
                layers_btn.place(relx=0.02, rely=0.02)
            except Exception:
                layers_btn.grid(row=2, column=3, padx=5, pady=5)

            # Map click -> goto handler
            def _on_map_click(data):
                # data can be (lat, lon) or an object depending on tkintermapview version
                try:
                    if isinstance(data, (list, tuple)):
                        lat, lon = float(data[0]), float(data[1])
                    else:
                        # try common attributes
                        lat = getattr(data, 'lat', None) or getattr(data, 'latitude', None) or getattr(data, 'y', None)
                        lon = getattr(data, 'lng', None) or getattr(data, 'longitude', None) or getattr(data, 'x', None)
                        lat = float(lat)
                        lon = float(lon)
                except Exception:
                    # some versions call with an event; try to convert pixel->geo
                    try:
                        # data may be a Tk event with x/y
                        ex = getattr(data, 'x', None)
                        ey = getattr(data, 'y', None)
                        if ex is not None and ey is not None:
                            try:
                                lat, lon = map_widget.get_position(ex, ey)
                            except Exception:
                                lat, lon = map_widget.convert_canvas_coords_to_decimal_coords(ex, ey)
                        else:
                            return
                    except Exception:
                        return

                # Use current drone altitude if available, else fallback to altitude slider or 10m
                try:
                    current_alt = None
                    try:
                        current_alt = float(dron.alt)
                    except Exception:
                        current_alt = None
                    if current_alt is None or current_alt == 0:
                        try:
                            current_alt = float(altitudeSldr.get())
                        except Exception:
                            current_alt = 10.0
                except Exception:
                    current_alt = 10.0

                # Send goto command (non-blocking)
                try:
                    dron.goto(lat, lon, current_alt, blocking=False)
                    # brief feedback in UI: show coords in a small overlay on the map for 1s
                    try:
                        # remove previous overlay if present
                        if hasattr(map_widget, '_coord_overlay') and map_widget._coord_overlay:
                            try:
                                map_widget._coord_overlay.destroy()
                            except Exception:
                                pass
                        overlay = tk.Label(right_frame, text=f'{lat:.6f}, {lon:.6f}', bg='white', fg='black', bd=1, relief=tk.SOLID)
                        # place overlay near top-left of map (small margin)
                        overlay.place(relx=0.02, rely=0.02)
                        map_widget._coord_overlay = overlay
                        # destroy after 1 second
                        overlay.after(1000, lambda: (overlay.destroy(), setattr(map_widget, '_coord_overlay', None)))
                        try:
                            stateShowLbl['text'] = f'GOTO -> {round(lat,6)},{round(lon,6)}'
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception as e:
                    # show inline error instead of modal dialog
                    try:
                        err_lbl = tk.Label(right_frame, text=f'Error goto: {e}', bg='white', fg='red', bd=1, relief=tk.SOLID)
                        err_lbl.place(relx=0.02, rely=0.02)
                        err_lbl.after(2000, lambda: err_lbl.destroy())
                    except Exception:
                        pass

            # Register click handler - try official API first, then fallbacks
            try:
                if hasattr(map_widget, 'add_left_click_map_command'):
                    map_widget.add_left_click_map_command(_on_map_click)
                elif hasattr(map_widget, 'add_left_click_map_callback'):
                    map_widget.add_left_click_map_callback(_on_map_click)
                else:
                    # fallback: bind canvas click and convert pixels to geo
                    cvs = getattr(map_widget, 'canvas', None) or getattr(map_widget, 'map_canvas', None)
                    if cvs:
                        def _pixel_click(evt):
                            try:
                                # try map_widget.get_position(x,y)
                                latlon = None
                                try:
                                    latlon = map_widget.get_position(evt.x, evt.y)
                                except Exception:
                                    try:
                                        latlon = map_widget.convert_canvas_coords_to_decimal_coords(evt.x, evt.y)
                                    except Exception:
                                        latlon = None
                                if latlon:
                                    _on_map_click(latlon)
                            except Exception:
                                pass
                        cvs.bind('<Button-1>', _pixel_click)
            except Exception:
                pass
        except Exception as e:
            tk.Label(right_frame, text=f'Error iniciando mapa: {e}').pack(fill=tk.BOTH, expand=True)
    else:
        tk.Label(right_frame, text='Instala tkintermapview:\npython -m pip install tkintermapview').pack(fill=tk.BOTH, expand=True)

    return ventana


if __name__ == '__main__':
    ventana = crear_ventana()
    # Check for command-line args passed by launcher
    try:
        mode = None
        com = None
        argv = sys.argv[1:]
        if argv:
            # simple arg parsing: --mode sim  or --mode esc --com COM3
            i = 0
            while i < len(argv):
                a = argv[i]
                if a == '--mode' and i+1 < len(argv):
                    mode = argv[i+1]
                    i += 2
                elif a == '--com' and i+1 < len(argv):
                    com = argv[i+1]
                    i += 2
                else:
                    i += 1
        if mode:
            # schedule connect after mainloop starts to avoid UI race
            ventana.after(200, lambda: connect_auto(mode, com))
    except Exception:
        pass
    ventana.mainloop()
