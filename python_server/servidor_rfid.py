"""
MV
SERVIDOR RFID SIMPLE - Solo muestra UID HEX y DEC
CORREGIDO: Muestra historial completo
VERSIÓN MEJORADA: Con CORS manual para ESP32
"""
from flask import Flask, request, jsonify
from datetime import datetime
import socket

app = Flask(__name__)
registros = []

# ============================================
# CORS MANUAL - Para permitir ESP32
# ============================================
@app.after_request
def add_cors_headers(response):
    """Agrega headers CORS manualmente para ESP32"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📡 RFID Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        h1 {
            color: #4a5568;
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        
        .status {
            background: #48bb78;
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 0.9em;
            display: inline-block;
            margin-top: 10px;
            font-weight: 600;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            border: 1px solid #e2e8f0;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card h3 {
            color: #718096;
            font-size: 1em;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-value {
            font-size: 2.8em;
            font-weight: 800;
            color: #4a5568;
        }
        
        .registros-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }
        
        .registros-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #edf2f7;
        }
        
        .registros-header h2 {
            color: #4a5568;
            font-size: 1.5em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .registros-list {
            max-height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .registro-card {
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 5px solid #667eea;
            transition: all 0.3s ease;
            display: grid;
            grid-template-columns: 1fr 2fr 2fr;
            gap: 20px;
            align-items: center;
        }
        
        .registro-card:hover {
            transform: translateX(5px);
            background: #edf2f7;
        }
        
        .registro-time {
            font-size: 0.9em;
            color: #718096;
            font-weight: 600;
            background: #e2e8f0;
            padding: 5px 15px;
            border-radius: 20px;
            text-align: center;
        }
        
        .uid-section {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .uid-label {
            font-size: 0.8em;
            color: #718096;
            font-weight: 600;
        }
        
        .uid-value {
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            font-weight: 700;
        }
        
        .uid-hex {
            color: #4c51bf;
        }
        
        .uid-dec {
            color: #38a169;
        }
        
        .empty-state {
            text-align: center;
            padding: 50px 20px;
            color: #a0aec0;
        }
        
        .empty-state i {
            font-size: 3em;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        /* Scrollbar personalizada */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
        }
        
        /* Animación para nuevos registros */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .new-registro {
            animation: fadeIn 0.5s ease-out;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            .registro-card {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            
            .registro-time {
                text-align: left;
                display: inline-block;
                width: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                <span>📡</span>
                RFID Monitor
            </h1>
            <div class="status">
                ✅ Servidor activo - Esperando lecturas
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 Total Lecturas</h3>
                <div class="stat-value" id="totalCount">0</div>
            </div>
            <div class="stat-card">
                <h3>⏰ Última Lectura</h3>
                <div class="stat-value" id="lastTime">--:--:--</div>
            </div>
            <div class="stat-card">
                <h3>🔗 Estado ESP32</h3>
                <div class="stat-value" style="color: #38a169;" id="espStatus">🟢 Conectado</div>
            </div>
        </div>
        
        <div class="registros-container">
            <div class="registros-header">
                <h2>
                    <span>📋</span>
                    Historial de Lecturas
                </h2>
                <button onclick="clearRegistros()" style="
                    background: #fc8181;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                ">
                    🗑️ Limpiar Historial
                </button>
            </div>
            
            <div class="registros-list" id="registrosList">
                <div class="empty-state" id="emptyState">
                    <div>📭</div>
                    <h3>No hay lecturas aún</h3>
                    <p>Acerca una tarjeta RFID al lector para comenzar</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let lastTotal = 0;
        
        function updateUI(data) {
            // Actualizar contadores
            document.getElementById('totalCount').textContent = data.total;
            
            if (data.registros.length > 0) {
                document.getElementById('lastTime').textContent = data.registros[0].timestamp;
                document.getElementById('emptyState').style.display = 'none';
                
                // Verificar si hay nuevos registros
                if (data.total !== lastTotal) {
                    lastTotal = data.total;
                    
                    // Actualizar lista COMPLETA
                    const registrosList = document.getElementById('registrosList');
                    let html = '';
                    
                    data.registros.forEach(registro => {
                        html += `
                            <div class="registro-card">
                                <div class="registro-time">${registro.timestamp}</div>
                                <div class="uid-section">
                                    <div class="uid-label">UID HEX</div>
                                    <div class="uid-value uid-hex">${registro.uid_hex}</div>
                                </div>
                                <div class="uid-section">
                                    <div class="uid-label">UID DEC</div>
                                    <div class="uid-value uid-dec">${registro.uid_dec}</div>
                                </div>
                            </div>
                        `;
                    });
                    
                    registrosList.innerHTML = html;
                    
                    // Mostrar notificación solo para nueva lectura
                    if (data.total > lastTotal) {
                        showNotification('Nueva lectura RFID recibida');
                    }
                }
            } else {
                document.getElementById('emptyState').style.display = 'block';
            }
        }
        
        function fetchRegistros() {
            fetch('/api/registros')
                .then(response => response.json())
                .then(data => updateUI(data))
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('espStatus').textContent = '🔴 Error';
                    document.getElementById('espStatus').style.color = '#fc8181';
                });
        }
        
        function showNotification(message) {
            // Crear notificación temporal
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 1000;
                animation: fadeIn 0.3s ease-out;
                font-weight: 600;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
        
        function clearRegistros() {
            if (confirm('¿Borrar todo el historial de lecturas?')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'cleared') {
                            showNotification('Historial borrado');
                            lastTotal = 0;
                            fetchRegistros();
                        }
                    });
            }
        }
        
        // Actualizar cada 2 segundos
        setInterval(fetchRegistros, 2000);
        
        // Cargar datos iniciales
        window.onload = fetchRegistros;
        
        // Agregar estilo para fadeOut
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes fadeOut {
                from { opacity: 1; transform: translateX(0); }
                to { opacity: 0; transform: translateX(100px); }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/api/rfid', methods=['POST'])
def recibir_rfid():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibió JSON"}), 400
        
        uid_hex = data.get('uid_hex', 'N/A')
        uid_dec = data.get('uid_dec', 'N/A')
        device = data.get('device', 'ESP32')
        
        registro = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "uid_hex": uid_hex,
            "uid_dec": uid_dec,
            "device": device
        }
        
        registros.append(registro)
        
        # Limitar a 50 registros
        if len(registros) > 50:
            registros.pop(0)
        
        # Mostrar en consola
        print(f"\n{'='*60}")
        print(f"📡 DATOS RECIBIDOS DE: {device}")
        print(f"🕐 Hora: {registro['timestamp']}")
        print(f"🎫 UID HEX: {uid_hex}")
        print(f"🔢 UID DEC: {uid_dec}")
        print(f"📊 Total en historial: {len(registros)}")
        print(f"{'='*60}")
        
        return jsonify({
            "status": "success",
            "message": "UID recibido exitosamente",
            "total_registros": len(registros),
            "timestamp": registro['timestamp']
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR en /api/rfid: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/registros', methods=['GET'])
def get_registros():
    """Devuelve TODOS los registros"""
    return jsonify({
        "total": len(registros),
        "registros": registros[::-1]  # Últimos primero
    })

@app.route('/api/registros_completos', methods=['GET'])
def get_registros_completos():
    """Endpoint alternativo"""
    return jsonify({
        "total": len(registros),
        "registros": registros
    })

@app.route('/api/clear', methods=['POST'])
def clear_registros():
    """Limpia todos los registros"""
    registros.clear()
    return jsonify({
        "status": "cleared",
        "message": "Historial borrado",
        "total": 0
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está activo"""
    return jsonify({
        "status": "online",
        "registros": len(registros),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

def get_server_info():
    """Obtiene información del servidor"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

if __name__ == '__main__':
    server_ip = get_server_info()
    
    print("\n" + "="*70)
    print("🚀 RFID MONITOR - Servidor Listo")
    print("="*70)
    print(f"🌐 Interfaz Web Local:  http://localhost:5000")
    print(f"🌐 Interfaz Web Red:    http://{server_ip}:5000")
    print(f"📡 Endpoint ESP32:      http://{server_ip}:5000/api/rfid")
    print(f"📋 Historial API:       http://{server_ip}:5000/api/registros")
    print(f"❤️  Health Check:        http://{server_ip}:5000/api/health")
    print("="*70)
    print("🎫 ESP32 debe enviar POST con JSON a: /api/rfid")
    print("   Ejemplo: {'uid_hex': 'A1 B2 C3 D4', 'uid_dec': '2717339292'}")
    print("="*70)
    print("⏳ Esperando lecturas RFID desde ESP32...")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)