
const usuario = "joaquin";

// ── Broker MQTT ──────────────────────────────────────────────────
const BROKER_HOST     = 'dronseetac.upc.edu';
const BROKER_PORT     = 8000;
const BROKER_PROTOCOL = 'ws';
const BROKER_PATH     = '/mqtt';
const BROKER_USERNAME = 'dronsEETAC';
const BROKER_PASSWORD = 'mimara1456.';

const brokerUrl = `${BROKER_PROTOCOL}://${BROKER_HOST}:${BROKER_PORT}${BROKER_PATH}`;

var despegueIniciado  = false;
var aterrizajeIniciado = false;
var rtlIniciado       = false;

// ── Mapa (Leaflet) ───────────────────────────────────────────────
var mapa       = null;
var marcador   = null;
var trayectoria = null;
var puntosRuta = [];
var mapaIniciado = false;

function iniciarMapa() {
    if (mapaIniciado) return;
    mapaIniciado = true;

    // Centro por defecto: EETAC (Castelldefels)
    mapa = L.map('map').setView([41.2756, 1.9879], 17);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(mapa);

    // Icono del dron
    const iconoDron = L.divIcon({
        html: '🚁',
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14]
    });

    marcador   = L.marker([41.2756, 1.9879], { icon: iconoDron }).addTo(mapa);
    trayectoria = L.polyline([], { color: '#008CBA', weight: 3 }).addTo(mapa);
}

function actualizarMapa(lat, lon) {
    if (!mapa) return;
    const pos = [lat, lon];
    marcador.setLatLng(pos);
    puntosRuta.push(pos);
    trayectoria.setLatLngs(puntosRuta);
    // Centrar el mapa en la posición del dron
    mapa.setView(pos);

    document.getElementById('mapaLat').innerText = lat.toFixed(6);
    document.getElementById('mapaLon').innerText = lon.toFixed(6);
}

// ── Video WebRTC ─────────────────────────────────────────────────
var peerConnection = null;

async function conectarVideo() {
    if (peerConnection) await desconectarVideo();

    const host = document.getElementById('cameraHost').value.trim();
    const url  = `http://${host}/offer`;
    const estado = document.getElementById('videoEstado');
    estado.innerText = 'Conectando…';

    try {
        peerConnection = new RTCPeerConnection();

        // Cuando llegue la pista de vídeo del servidor, asignarla al <video>
        peerConnection.ontrack = (event) => {
            document.getElementById('videoStream').srcObject = event.streams[0];
            estado.innerText = '';
        };

        peerConnection.onconnectionstatechange = () => {
            const s = peerConnection.connectionState;
            if (s === 'disconnected' || s === 'failed') {
                estado.innerText = 'Conexión perdida.';
            }
        };

        // Declaramos que solo queremos recibir vídeo (no audio ni enviar nada)
        peerConnection.addTransceiver('video', { direction: 'recvonly' });

        // Crear oferta y esperar a que ICE gathering termine antes de enviarla
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);

        await new Promise((resolve) => {
            if (peerConnection.iceGatheringState === 'complete') {
                resolve();
            } else {
                const check = () => {
                    if (peerConnection.iceGatheringState === 'complete') {
                        peerConnection.removeEventListener('icegatheringstatechange', check);
                        resolve();
                    }
                };
                peerConnection.addEventListener('icegatheringstatechange', check);
            }
        });

        // Enviar oferta al CameraService y recibir la respuesta
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sdp:  peerConnection.localDescription.sdp,
                type: peerConnection.localDescription.type,
            }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const answer = await resp.json();
        await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));

    } catch (e) {
        estado.innerText = 'Error: ' + e.message;
        console.error('WebRTC error:', e);
    }
}

async function desconectarVideo() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    document.getElementById('videoStream').srcObject = null;
    document.getElementById('videoEstado').innerText = 'Desconectado.';
}

// ── MQTT ─────────────────────────────────────────────────────────
console.log('Conectando al broker MQTT en', brokerUrl);
const client = mqtt.connect(brokerUrl, {
    clean: false,
    keepalive: 60,
    clientId: 'webapp_' + usuario + Math.random().toString(16).substr(2, 8),
    username: BROKER_USERNAME,
    password: BROKER_PASSWORD,
});

client.on('connect', () => {
    console.log('Conectado al broker');
    client.subscribe('autopilotServiceDemo/' + usuario + '/#');
});

client.on('message', (topic, message) => {
    if (topic.includes("telemetryInfo")) {
        try {
            const data = JSON.parse(message.toString());

            // ── Altitud y estado (barra superior) ──
            if (data.alt !== undefined) {
                document.getElementById("altitudValor").innerText = parseFloat(data.alt).toFixed(2);
            }
            if (data.state !== undefined) {
                const estado = data.state;
                document.getElementById("estadoDron").innerText = "Estado: " + estado;

                if (estado === "flying" && despegueIniciado) {
                    document.getElementById('botonDespegar').classList.replace('boton-amarillo', 'boton-verde');
                    despegueIniciado = false;
                }
                if (estado === "landing" && aterrizajeIniciado) {
                    document.getElementById('botonAterrizar').classList.replace('boton-verde', 'boton-amarillo');
                }
                if (estado === "connected" && aterrizajeIniciado) {
                    document.getElementById('botonAterrizar').classList.replace('boton-amarillo', 'boton-verde');
                    aterrizajeIniciado = false;
                }
                if (estado === "returning" && rtlIniciado) {
                    document.getElementById('botonRTL').classList.replace('boton-verde', 'boton-amarillo');
                }
                if (estado === "connected" && rtlIniciado) {
                    document.getElementById('botonRTL').classList.replace('boton-amarillo', 'boton-verde');
                    rtlIniciado = false;
                }
            }

            // ── Posición GPS → mapa ──
            if (data.lat !== undefined && data.lon !== undefined) {
                actualizarMapa(parseFloat(data.lat), parseFloat(data.lon));
            }

        } catch (e) { console.error("Error en telemetría", e); }
    }
});

// ── Funciones de control ─────────────────────────────────────────
function conectarDron() {
    client.publish(usuario + '/autopilotServiceDemo/connect', "");
    document.getElementById('botonConectar').classList.add('boton-verde');
    client.publish(usuario + '/autopilotServiceDemo/startTelemetry', "");
}

function despegarDron() {
    const alturaInput = document.getElementById('altura').value;
    if (alturaInput) {
        client.publish(usuario + '/autopilotServiceDemo/arm_takeOff', String(alturaInput));
        despegueIniciado = true;
        document.getElementById('botonDespegar').classList.add('boton-amarillo');
        document.getElementById('botonAterrizar').classList.remove('boton-verde', 'boton-amarillo');
        document.getElementById('botonRTL').classList.remove('boton-verde', 'boton-amarillo');
    }
}

function aterrizarDron() {
    client.publish(usuario + '/autopilotServiceDemo/Land', "");
    aterrizajeIniciado = true;
    document.getElementById('botonAterrizar').classList.add('boton-amarillo');
    document.getElementById('botonDespegar').classList.remove('boton-verde', 'boton-amarillo');
}

function rtlDron() {
    client.publish(usuario + '/autopilotServiceDemo/RTL', "");
    rtlIniciado = true;
    document.getElementById('botonRTL').classList.add('boton-amarillo');
    document.getElementById('botonDespegar').classList.remove('boton-verde', 'boton-amarillo');
}

function moverDron(direction) {
    client.publish(usuario + '/autopilotServiceDemo/go', direction);
}

function cambiarHeading(val) {
    client.publish(usuario + '/autopilotServiceDemo/changeHeading', String(val));
    document.getElementById('headingVal').innerText = val;
}
