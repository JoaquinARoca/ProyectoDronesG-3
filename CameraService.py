###########  INSTALAR #########################
# opencv-python
# aiortc  (incluye aiohttp y av como dependencias)
###############################################

import asyncio
import json
import fractions
import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

pcs = set()


class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id):
        super().__init__()
        print("Preparando la cámara...")
        self.cap = cv2.VideoCapture(camera_id)
        self.frame_count = 0

    async def recv(self):
        self.frame_count += 1
        ret, frame = self.cap.read()
        if not ret:
            print("Error al leer frame de la cámara")
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)
        return video_frame


# Cabeceras CORS para que el navegador (puerto 5002) pueda llamar al CameraService (puerto 9999)
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}


async def offer_handler(request):
    # Preflight CORS
    if request.method == 'OPTIONS':
        return web.Response(headers=CORS_HEADERS)

    # El navegador envía su oferta SDP
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on('connectionstatechange')
    async def on_connectionstatechange():
        print(f"Estado conexión WebRTC: {pc.connectionState}")
        if pc.connectionState in ('failed', 'closed'):
            await pc.close()
            pcs.discard(pc)

    # Añadir la pista de vídeo de la cámara
    camera_id = request.app['camera_id']
    pc.addTrack(CustomVideoStreamTrack(camera_id))

    # Procesar oferta y generar respuesta
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type='application/json',
        body=json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type,
        }),
        headers=CORS_HEADERS,
    )


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def main():
    camera_id = 0  # Cambiar si el vídeo del dron viene de otra fuente
    app = web.Application()
    app['camera_id'] = camera_id
    app.router.add_route('OPTIONS', '/offer', offer_handler)
    app.router.add_post('/offer', offer_handler)
    app.on_shutdown.append(on_shutdown)
    print("CameraService arrancado en http://0.0.0.0:9999")
    web.run_app(app, host='0.0.0.0', port=9999)


if __name__ == '__main__':
    main()
