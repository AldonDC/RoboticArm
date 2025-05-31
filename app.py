from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import serial
import json
import threading
import time
import os
from datetime import datetime
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robotic_arm_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

# Crear directorios necesarios
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('templates', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

class RoboticArmController:
    def __init__(self):
        self.serial_connection = None
        self.servo_angles = {"servo1": 90, "servo2": 90, "servo3": 90, "servo4": 90}
        self.is_connected = False
        self.current_port = None
        self.connection_log = []
        self.last_command_time = None
        self.custom_settings = {
            'background_color': '#667eea',
            'secondary_color': '#764ba2', 
            'accent_color': '#00d4ff',
            'text_color': '#ffffff',
            'card_opacity': '0.1',
            'background_image': None,
            'theme_mode': 'dark',
            'particle_count': 8,
            'glow_effect': True,
            'blur_effect': True,
            'animation_speed': 'normal'
        }
        
    def connect_serial(self, port, baudrate=115200):
        """Conecta al puerto serial"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            self.serial_connection = serial.Serial(port, baudrate, timeout=1)
            self.is_connected = True
            self.current_port = port
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'type': 'success',
                'message': f'Conectado a {port}'
            }
            self.connection_log.append(log_entry)
            
            return True, f"Conectado exitosamente a {port}"
        except Exception as e:
            self.is_connected = False
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'type': 'error',
                'message': f'Error conectando a {port}: {str(e)}'
            }
            self.connection_log.append(log_entry)
            return False, str(e)
    
    def disconnect_serial(self):
        """Desconecta del puerto serial"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.is_connected = False
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'type': 'info',
                'message': 'Desconectado del puerto serial'
            }
            self.connection_log.append(log_entry)
            return True
        except Exception as e:
            return False
    
    def send_command(self, servo_data):
        """Envía comando a los servomotores"""
        if not self.is_connected or not self.serial_connection:
            return False, "No conectado al puerto serial"
        
        try:
            self.servo_angles.update(servo_data)
            json_data = json.dumps(self.servo_angles)
            self.serial_connection.write((json_data + '\n').encode())
            
            self.last_command_time = datetime.now().strftime('%H:%M:%S')
            
            log_entry = {
                'timestamp': self.last_command_time,
                'type': 'command',
                'message': f'Comando enviado: {json_data}'
            }
            self.connection_log.append(log_entry)
            
            # Mantener solo los últimos 50 logs
            if len(self.connection_log) > 50:
                self.connection_log = self.connection_log[-50:]
            
            return True, json_data
        except Exception as e:
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'type': 'error',
                'message': f'Error enviando comando: {str(e)}'
            }
            self.connection_log.append(log_entry)
            return False, str(e)
    
    def get_status(self):
        """Obtiene el estado actual del sistema"""
        return {
            'connected': self.is_connected,
            'port': self.current_port,
            'servo_angles': self.servo_angles,
            'last_command': self.last_command_time,
            'log': self.connection_log[-10:],  # Últimos 10 logs
            'settings': self.custom_settings
        }
    
    def update_settings(self, settings):
        """Actualiza la configuración personalizada"""
        self.custom_settings.update(settings)
        return self.custom_settings

# Instancia global del controlador
controller = RoboticArmController()

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rutas de API existentes...
@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def connect():
    """API para conectar al puerto serial"""
    data = request.get_json()
    port = data.get('port', '/dev/ttyUSB0')
    baudrate = data.get('baudrate', 115200)
    
    success, message = controller.connect_serial(port, baudrate)
    
    # Emitir estado actualizado a todos los clientes
    socketio.emit('status_update', controller.get_status())
    
    return jsonify({
        'success': success,
        'message': message,
        'status': controller.get_status()
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """API para desconectar del puerto serial"""
    success = controller.disconnect_serial()
    
    # Emitir estado actualizado a todos los clientes
    socketio.emit('status_update', controller.get_status())
    
    return jsonify({
        'success': success,
        'status': controller.get_status()
    })

@app.route('/api/servo', methods=['POST'])  
def control_servo():
    """API para controlar servomotores"""
    data = request.get_json()
    success, message = controller.send_command(data)
    
    # Emitir comando en tiempo real a todos los clientes
    socketio.emit('servo_update', {
        'angles': controller.servo_angles,
        'success': success,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    return jsonify({
        'success': success,
        'message': message,
        'angles': controller.servo_angles
    })

@app.route('/api/status')
def get_status():
    """API para obtener el estado actual"""
    return jsonify(controller.get_status())

@app.route('/api/reset')
def reset_servos():
    """API para resetear servomotores a posición inicial"""
    reset_data = {"servo1": 90, "servo2": 90, "servo3": 90, "servo4": 90}
    success, message = controller.send_command(reset_data)
    
    # Emitir reset a todos los clientes
    socketio.emit('servo_reset', controller.servo_angles)
    
    return jsonify({
        'success': success,
        'message': message,
        'angles': controller.servo_angles
    })

@app.route('/api/upload_background', methods=['POST'])
def upload_background():
    """API para subir imagen de fondo"""
    if 'background' not in request.files:
        return jsonify({'success': False, 'message': 'No se encontró archivo'})
    
    file = request.files['background']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No se seleccionó archivo'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"background_{int(time.time())}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Actualizar configuración
        controller.custom_settings['background_image'] = filename
        
        # Emitir cambio a todos los clientes
        socketio.emit('background_updated', {'image': filename})
        
        return jsonify({
            'success': True,
            'message': 'Imagen de fondo actualizada',
            'filename': filename
        })
    
    return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'})

@app.route('/api/remove_background', methods=['POST'])
def remove_background():
    """API para quitar imagen de fondo"""
    controller.custom_settings['background_image'] = None
    
    # Emitir cambio a todos los clientes
    socketio.emit('background_updated', {'image': None})
    
    return jsonify({
        'success': True,
        'message': 'Imagen de fondo removida'
    })

@app.route('/api/update_theme', methods=['POST'])
def update_theme():
    """API para actualizar configuración del tema"""
    data = request.get_json()
    
    # Actualizar configuración
    settings = controller.update_settings(data)
    
    # Emitir cambios a todos los clientes
    socketio.emit('theme_updated', settings)
    
    return jsonify({
        'success': True,
        'message': 'Tema actualizado',
        'settings': settings
    })

@app.route('/api/save_theme', methods=['POST'])
def save_theme():
    """API para guardar tema personalizado"""
    data = request.get_json()
    theme_name = data.get('name', 'Custom Theme')
    
    # Aquí podrías guardar en una base de datos o archivo
    # Por simplicidad, solo devolvemos éxito
    return jsonify({
        'success': True,
        'message': f'Tema "{theme_name}" guardado exitosamente'
    })

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('connect')
def handle_connect():
    """Maneja nuevas conexiones WebSocket"""
    emit('status_update', controller.get_status())

@socketio.on('servo_control')
def handle_servo_control(data):
    """Maneja control de servos en tiempo real via WebSocket"""
    success, message = controller.send_command(data)
    
    # Emitir a todos los clientes conectados
    emit('servo_update', {
        'angles': controller.servo_angles,
        'success': success,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, broadcast=True)

if __name__ == '__main__':
    # Crear directorio templates si no existe
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Crear archivo HTML mejorado
    html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Control de Brazo Robótico - Personalizable</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --accent-color: #00d4ff;
            --text-color: #ffffff;
            --card-opacity: 0.1;
            --blur-intensity: 10px;
            --glow-intensity: 20px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            min-height: 100vh;
            color: var(--text-color);
            transition: all 0.5s ease;
            position: relative;
            overflow-x: hidden;
        }

        body.has-background {
            background-image: var(--bg-image);
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        body.has-background::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, var(--primary-color)80, var(--secondary-color)80);
            z-index: -1;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 10;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            position: relative;
        }

        .header h1 {
            font-size: clamp(2rem, 4vw, 3rem);
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            animation: glow 2s ease-in-out infinite alternate;
            background: linear-gradient(45deg, var(--accent-color), #fff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        @keyframes glow {
            from { 
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3), 0 0 var(--glow-intensity) rgba(255,255,255,0.3); 
            }
            to { 
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3), 0 0 calc(var(--glow-intensity) * 1.5) rgba(255,255,255,0.5); 
            }
        }

        .theme-controls {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, var(--card-opacity));
            backdrop-filter: blur(var(--blur-intensity));
            border-radius: 15px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            max-width: 300px;
            transform: translateX(calc(100% - 60px));
            transition: transform 0.3s ease;
        }

        .theme-controls:hover,
        .theme-controls.expanded {
            transform: translateX(0);
        }

        .theme-toggle {
            position: absolute;
            left: -45px;
            top: 50%;
            transform: translateY(-50%);
            background: var(--accent-color);
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
            font-size: 18px;
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
            transition: all 0.3s ease;
        }

        .theme-toggle:hover {
            transform: translateY(-50%) scale(1.1);
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
        }

        .color-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 10px 0;
        }

        .color-input-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .color-input-group label {
            font-size: 12px;
            opacity: 0.8;
            font-weight: 600;
        }

        .color-input {
            width: 100%;
            height: 40px;
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: transparent;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .color-input:hover {
            border-color: var(--accent-color);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
        }

        .status-card {
            background: rgba(255, 255, 255, var(--card-opacity));
            backdrop-filter: blur(var(--blur-intensity));
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }

        .connection-section {
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 15px;
            align-items: center;
            margin-bottom: 15px;
        }

        .input-group {
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 12px 15px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-color);
            font-size: 16px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            border-color: var(--accent-color);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: all 0.5s ease;
        }

        .btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .btn-primary {
            background: linear-gradient(45deg, var(--accent-color), #0099cc);
            color: white;
        }

        .btn-danger {
            background: linear-gradient(45deg, #ff6b6b, #d63031);
            color: white;
        }

        .btn-success {
            background: linear-gradient(45deg, #00b894, #00cec9);
            color: white;
        }

        .btn-theme {
            background: linear-gradient(45deg, #a29bfe, #6c5ce7);
            color: white;
            font-size: 12px;
            padding: 8px 16px;
        }

        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
            margin: 10px 0;
        }

        .file-input {
            position: absolute;
            left: -9999px;
        }

        .file-input-label {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 12px;
            background: linear-gradient(45deg, #fd79a8, #e84393);
            color: white;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 12px;
        }

        .file-input-label:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(232, 67, 147, 0.4);
        }

        .servo-controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .servo-card {
            background: rgba(255, 255, 255, var(--card-opacity));
            backdrop-filter: blur(var(--blur-intensity));
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .servo-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: left 0.5s ease;
        }

        .servo-card:hover::before {
            left: 100%;
        }

        .servo-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
        }

        .servo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .servo-title {
            font-size: 1.2rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .servo-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-color);
            text-shadow: 0 0 var(--glow-intensity) rgba(0, 212, 255, 0.5);
            position: relative;
        }

        .slider-container {
            position: relative;
            margin: 15px 0;
        }

        .slider {
            width: 100%;
            height: 10px;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.2);
            outline: none;
            -webkit-appearance: none;
            appearance: none;
            position: relative;
        }

        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: linear-gradient(45deg, var(--accent-color), #0099cc);
            cursor: pointer;
            box-shadow: 0 0 var(--glow-intensity) rgba(0, 212, 255, 0.5);
            transition: all 0.3s ease;
            position: relative;
        }

        .slider::-webkit-slider-thumb:hover {
            transform: scale(1.3);
            box-shadow: 0 0 calc(var(--glow-intensity) * 1.5) rgba(0, 212, 255, 0.8);
        }

        .control-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }

        .floating-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
        }

        .particle {
            position: absolute;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 6s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { 
                transform: translateY(0px) rotate(0deg); 
                opacity: 0.3;
            }
            50% { 
                transform: translateY(-30px) rotate(180deg); 
                opacity: 0.8;
            }
        }

        .log-section {
            margin-top: 20px;
        }

        .log-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            border-radius: 3px;
            transition: all 0.3s ease;
        }

        .log-entry:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.1);
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-connected { background-color: #00ff88; }
        .status-disconnected { background-color: #ff4757; }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.1); }
            100% { opacity: 1; transform: scale(1); }
        }

        .theme-presets {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 15px 0;
        }

        .preset-btn {
            padding: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            background: transparent;
            color: var(--text-color);
            cursor: pointer;
            font-size: 11px;
            transition: all 0.3s ease;
        }

        .preset-btn:hover {
            background: rgba(255,255,255,0.1);
            border-color: var(--accent-color);
        }

        /* Responsive */
        @media (max-width: 768px) {
            .theme-controls {
                position: relative;
                top: auto;
                right: auto;
                transform: none;
                max-width: none;
                margin-bottom: 20px;
            }

            .theme-toggle {
                display: none;
            }

            .connection-section {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            
            .servo-controls {
                grid-template-columns: 1fr;
            }
            
            .control-buttons {
                flex-direction: column;
            }

            .color-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Efectos especiales */
        .glow-effect {
            animation: rainbow-glow 3s ease-in-out infinite;
        }

        @keyframes rainbow-glow {
            0% { box-shadow: 0 0 20px #ff0080; }
            25% { box-shadow: 0 0 20px #00ff80; }
            50% { box-shadow: 0 0 20px #8000ff; }
            75% { box-shadow: 0 0 20px #ff8000; }
            100% { box-shadow: 0 0 20px #ff0080; }
        }

        .pulse-animation {
            animation: pulseScale 0.3s ease;
        }

        @keyframes pulseScale {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        /* Modo oscuro/claro */
        .light-mode {
            --text-color: #333333;
        }

        .light-mode .status-card,
        .light-mode .servo-card,
        .light-mode .theme-controls {
            background: rgba(255, 255, 255, 0.9);
            color: #333;
        }

        .light-mode .input-group input {
            background: rgba(0, 0, 0, 0.1);
            color: #333;
        }
    </style>
</head>
<body>
    <!-- Partículas flotantes dinámicas -->
    <div class="floating-particles" id="particleContainer">
        <!-- Las partículas se generan dinámicamente -->
    </div>

    <!-- Panel de personalización -->
    <div class="theme-controls" id="themeControls">
        <button class="theme-toggle" onclick="toggleThemePanel()">
            <i class="fas fa-palette"></i>
        </button>
        
        <h4 style="margin-bottom: 15px; text-align: center;">🎨 Personalización</h4>
        
        <!-- Subir imagen de fondo -->
        <div class="file-input-wrapper">
            <input type="file" id="backgroundInput" class="file-input" accept="image/*" onchange="uploadBackground()">
            <label for="backgroundInput" class="file-input-label">
                <i class="fas fa-image"></i>
                Cambiar Fondo
            </label>
        </div>
        
        <button class="btn btn-theme" onclick="removeBackground()" style="width: 100%; margin-bottom: 10px;">
            <i class="fas fa-times"></i> Quitar Fondo
        </button>

        <!-- Presets de temas -->
        <div class="theme-presets">
            <button class="preset-btn" onclick="applyPreset('neon')">🌈 Neon</button>
            <button class="preset-btn" onclick="applyPreset('sunset')">🌅 Sunset</button>
            <button class="preset-btn" onclick="applyPreset('ocean')">🌊 Océano</button>
            <button class="preset-btn" onclick="applyPreset('space')">🚀 Espacio</button>
            <button class="preset-btn" onclick="applyPreset('forest')">🌲 Bosque</button>
            <button class="preset-btn" onclick="applyPreset('cyber')">🤖 Cyber</button>
        </div>

        <!-- Selector de colores -->
        <div class="color-grid">
            <div class="color-input-group">
                <label>Color Primario</label>
                <input type="color" class="color-input" id="primaryColor" value="#667eea" onchange="updateColors()">
            </div>
            <div class="color-input-group">
                <label>Color Secundario</label>
                <input type="color" class="color-input" id="secondaryColor" value="#764ba2" onchange="updateColors()">
            </div>
            <div class="color-input-group">
                <label>Color de Acento</label>
                <input type="color" class="color-input" id="accentColor" value="#00d4ff" onchange="updateColors()">
            </div>
            <div class="color-input-group">
                <label>Color de Texto</label>
                <input type="color" class="color-input" id="textColor" value="#ffffff" onchange="updateColors()">
            </div>
        </div>

        <!-- Controles adicionales -->
        <div style="margin: 15px 0;">
            <label style="display: block; margin-bottom: 5px; font-size: 12px;">Transparencia de Tarjetas</label>
            <input type="range" min="0.05" max="0.3" step="0.05" value="0.1" id="cardOpacity" onchange="updateEffects()" 
                   style="width: 100%; height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px;">
        </div>

        <div style="margin: 15px 0;">
            <label style="display: block; margin-bottom: 5px; font-size: 12px;">Intensidad de Blur</label>
            <input type="range" min="5" max="20" step="1" value="10" id="blurIntensity" onchange="updateEffects()"
                   style="width: 100%; height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px;">
        </div>

        <div style="margin: 15px 0;">
            <label style="display: block; margin-bottom: 5px; font-size: 12px;">Partículas (${particleCount})</label>
            <input type="range" min="0" max="20" step="1" value="8" id="particleCount" onchange="updateParticles()"
                   style="width: 100%; height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px;">
        </div>

        <!-- Interruptores de efectos -->
        <div style="display: flex; justify-content: space-between; margin: 15px 0;">
            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px;">
                <input type="checkbox" id="glowEffect" checked onchange="updateEffects()"> Efectos Glow
            </label>
            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px;">
                <input type="checkbox" id="lightMode" onchange="toggleLightMode()"> Modo Claro
            </label>
        </div>

        <button class="btn btn-success" onclick="saveCustomTheme()" style="width: 100%; margin-top: 10px;">
            <i class="fas fa-save"></i> Guardar Tema
        </button>
    </div>

    <div class="container">
        <div class="header">
            <h1>🤖 Control de Brazo Robótico</h1>
            <p>Sistema de Control Avanzado Personalizable</p>
        </div>

        <!-- Sección de Conexión -->
        <div class="status-card">
            <h3><i class="fas fa-plug"></i> Configuración de Conexión</h3>
            <div class="connection-section">
                <div class="input-group">
                    <input type="text" id="serialPort" placeholder="Puerto Serial (ej: /dev/ttyUSB0, COM3)" value="/dev/ttyUSB0">
                </div>
                <button class="btn btn-primary" onclick="connectSerial()">
                    <i class="fas fa-link"></i> Conectar
                </button>
                <button class="btn btn-danger" onclick="disconnectSerial()">
                    <i class="fas fa-unlink"></i> Desconectar
                </button>
            </div>
            <div class="status-indicator">
                <i class="fas fa-circle-dot"></i>
                Estado: <span class="status-dot status-disconnected" id="statusDot"></span>
                <span id="statusText">Desconectado</span>
            </div>
        </div>

        <!-- Controles de Servomotores -->
        <div class="servo-controls" id="servoControls">
            <!-- Los controles se generan dinámicamente -->
        </div>

        <!-- Botones de Control -->
        <div class="control-buttons">
            <button class="btn btn-success" onclick="resetServos()">
                <i class="fas fa-redo"></i> Reset Posición
            </button>
            <button class="btn btn-primary" onclick="savePreset()">
                <i class="fas fa-save"></i> Guardar Preset
            </button>
            <button class="btn btn-primary" onclick="loadPreset()">
                <i class="fas fa-folder-open"></i> Cargar Preset
            </button>
            <button class="btn btn-theme" onclick="randomColors()">
                <i class="fas fa-random"></i> Colores Aleatorios
            </button>
        </div>

        <!-- Log de Comandos -->
        <div class="status-card log-section">
            <h3><i class="fas fa-terminal"></i> Log de Comandos</h3>
            <div class="log-container" id="logContainer">
                <div class="log-entry log-info">🚀 Sistema iniciado - Esperando conexión...</div>
            </div>
        </div>
    </div>

    <script>
        // Configuración de Socket.IO
        const socket = io();
        
        // Variables globales
        let isConnected = false;
        let servoAngles = {servo1: 90, servo2: 90, servo3: 90, servo4: 90};
        let currentSettings = {
            background_color: '#667eea',
            secondary_color: '#764ba2', 
            accent_color: '#00d4ff',
            text_color: '#ffffff',
            card_opacity: '0.1',
            background_image: null,
            particle_count: 8,
            glow_effect: true,
            blur_effect: true
        };

        // Presets de temas
        const themePresets = {
            neon: {
                background_color: '#ff006e',
                secondary_color: '#8338ec',
                accent_color: '#00f5ff',
                text_color: '#ffffff'
            },
            sunset: {
                background_color: '#ff6b35',
                secondary_color: '#f7931e',
                accent_color: '#ffcd3c',
                text_color: '#ffffff'
            },
            ocean: {
                background_color: '#0077be',
                secondary_color: '#00a8cc',
                accent_color: '#40e0d0',
                text_color: '#ffffff'
            },
            space: {
                background_color: '#0d1b2a',
                secondary_color: '#415a77',
                accent_color: '#e0e1dd',
                text_color: '#ffffff'
            },
            forest: {
                background_color: '#2d5016',
                secondary_color: '#56ab2f',
                accent_color: '#a8e6cf',
                text_color: '#ffffff'
            },
            cyber: {
                background_color: '#1a1a2e',
                secondary_color: '#16213e',
                accent_color: '#0f3460',
                text_color: '#00ff41'
            }
        };

        // Inicializar interfaz
        document.addEventListener('DOMContentLoaded', function() {
            createServoControls();
            updateServoValues();
            createParticles();
            loadSavedTheme();
        });

        // Crear partículas dinámicas
        function createParticles() {
            const container = document.getElementById('particleContainer');
            container.innerHTML = '';
            
            const count = parseInt(document.getElementById('particleCount').value);
            
            for (let i = 0; i < count; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.top = Math.random() * 100 + '%';
                particle.style.width = (Math.random() * 6 + 2) + 'px';
                particle.style.height = particle.style.width;
                particle.style.animationDelay = Math.random() * 6 + 's';
                particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
                container.appendChild(particle);
            }
        }

        // Crear controles de servo dinámicamente
        function createServoControls() {
            const container = document.getElementById('servoControls');
            container.innerHTML = '';

            const servoIcons = ['🔧', '⚙️', '🔩', '🎛️'];

            for (let i = 1; i <= 4; i++) {
                const servoCard = document.createElement('div');
                servoCard.className = 'servo-card';
                servoCard.innerHTML = `
                    <div class="servo-header">
                        <div class="servo-title">${servoIcons[i-1]} Servo ${i}</div>
                        <div class="servo-value" id="servo${i}Value">90°</div>
                    </div>
                    <div class="slider-container">
                        <input type="range" class="slider" id="servo${i}Slider" 
                               min="0" max="180" value="90" 
                               oninput="updateServo('servo${i}', this.value)">
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; opacity: 0.7;">
                        <span>0°</span>
                        <span>90°</span>
                        <span>180°</span>
                    </div>
                `;
                container.appendChild(servoCard);
            }
        }

        // Funciones de personalización
        function toggleThemePanel() {
            const panel = document.getElementById('themeControls');
            panel.classList.toggle('expanded');
        }

        function updateColors() {
            const primary = document.getElementById('primaryColor').value;
            const secondary = document.getElementById('secondaryColor').value;
            const accent = document.getElementById('accentColor').value;
            const text = document.getElementById('textColor').value;

            const root = document.documentElement;
            root.style.setProperty('--primary-color', primary);
            root.style.setProperty('--secondary-color', secondary);
            root.style.setProperty('--accent-color', accent);
            root.style.setProperty('--text-color', text);

            // Actualizar configuración local
            currentSettings.background_color = primary;
            currentSettings.secondary_color = secondary;
            currentSettings.accent_color = accent;
            currentSettings.text_color = text;

            // Enviar al servidor
            updateThemeOnServer();
        }

        function updateEffects() {
            const cardOpacity = document.getElementById('cardOpacity').value;
            const blurIntensity = document.getElementById('blurIntensity').value;
            const glowEffect = document.getElementById('glowEffect').checked;

            const root = document.documentElement;
            root.style.setProperty('--card-opacity', cardOpacity);
            root.style.setProperty('--blur-intensity', blurIntensity + 'px');
            
            if (glowEffect) {
                root.style.setProperty('--glow-intensity', '20px');
            } else {
                root.style.setProperty('--glow-intensity', '0px');
            }

            currentSettings.card_opacity = cardOpacity;
            currentSettings.glow_effect = glowEffect;
            updateThemeOnServer();
        }

        function updateParticles() {
            const count = document.getElementById('particleCount').value;
            document.querySelector('label[style*="Partículas"]').innerHTML = `Partículas (${count})`;
            createParticles();
            currentSettings.particle_count = count;
        }

        function applyPreset(presetName) {
            const preset = themePresets[presetName];
            if (!preset) return;

            // Actualizar inputs de color
            document.getElementById('primaryColor').value = preset.background_color;
            document.getElementById('secondaryColor').value = preset.secondary_color;
            document.getElementById('accentColor').value = preset.accent_color;
            document.getElementById('textColor').value = preset.text_color;

            // Aplicar colores
            updateColors();

            addLog('info', `Tema ${presetName} aplicado`);
        }

        function randomColors() {
            const randomColor = () => '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
            
            document.getElementById('primaryColor').value = randomColor();
            document.getElementById('secondaryColor').value = randomColor();
            document.getElementById('accentColor').value = randomColor();
            
            updateColors();
            addLog('info', 'Colores aleatorios aplicados');
        }

        function toggleLightMode() {
            const isLight = document.getElementById('lightMode').checked;
            document.body.classList.toggle('light-mode', isLight);
            
            if (isLight) {
                document.getElementById('textColor').value = '#333333';
                updateColors();
            }
        }

        async function uploadBackground() {
            const fileInput = document.getElementById('backgroundInput');
            const file = fileInput.files[0];
            
            if (!file) return;

            const formData = new FormData();
            formData.append('background', file);

            try {
                const response = await fetch('/api/upload_background', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    setBackgroundImage(result.filename);
                    addLog('success', 'Imagen de fondo actualizada');
                } else {
                    addLog('error', result.message);
                }
            } catch (error) {
                addLog('error', 'Error subiendo imagen: ' + error.message);
            }
        }

        async function removeBackground() {
            try {
                const response = await fetch('/api/remove_background', {method: 'POST'});
                const result = await response.json();
                
                if (result.success) {
                    document.body.classList.remove('has-background');
                    document.body.style.removeProperty('--bg-image');
                    addLog('info', 'Imagen de fondo removida');
                }
            } catch (error) {
                addLog('error', 'Error removiendo fondo: ' + error.message);
            }
        }

        function setBackgroundImage(filename) {
            if (filename) {
                const imageUrl = `/static/uploads/${filename}`;
                document.body.style.setProperty('--bg-image', `url("${imageUrl}")`);
                document.body.classList.add('has-background');
            }
        }

        async function updateThemeOnServer() {
            try {
                await fetch('/api/update_theme', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(currentSettings)
                });
            } catch (error) {
                console.error('Error actualizando tema:', error);
            }
        }

        async function saveCustomTheme() {
            const themeName = prompt('Nombre para tu tema personalizado:', 'Mi Tema');
            if (!themeName) return;

            try {
                const response = await fetch('/api/save_theme', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: themeName,
                        settings: currentSettings
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    addLog('success', `Tema "${themeName}" guardado`);
                    
                    // Guardar en localStorage también
                    localStorage.setItem('customTheme', JSON.stringify(currentSettings));
                } else {
                    addLog('error', result.message);
                }
            } catch (error) {
                addLog('error', 'Error guardando tema: ' + error.message);
            }
        }

        function loadSavedTheme() {
            const saved = localStorage.getItem('customTheme');
            if (saved) {
                try {
                    const settings = JSON.parse(saved);
                    
                    // Aplicar configuración guardada
                    document.getElementById('primaryColor').value = settings.background_color || '#667eea';
                    document.getElementById('secondaryColor').value = settings.secondary_color || '#764ba2';
                    document.getElementById('accentColor').value = settings.accent_color || '#00d4ff';
                    document.getElementById('textColor').value = settings.text_color || '#ffffff';
                    
                    if (settings.card_opacity) {
                        document.getElementById('cardOpacity').value = settings.card_opacity;
                    }
                    
                    updateColors();
                    updateEffects();
                } catch (error) {
                    console.error('Error cargando tema guardado:', error);
                }
            }
        }

        // Funciones existentes del brazo robótico...
        async function connectSerial() {
            const port = document.getElementById('serialPort').value;
            if (!port) {
                addLog('error', 'Por favor ingresa un puerto serial');
                return;
            }

            try {
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({port: port, baudrate: 115200})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    isConnected = true;
                    updateStatus(true, `Conectado a ${port}`);
                    addLog('success', data.message);
                } else {
                    addLog('error', data.message);
                }
            } catch (error) {
                addLog('error', `Error de conexión: ${error.message}`);
            }
        }

        async function disconnectSerial() {
            try {
                const response = await fetch('/api/disconnect', {method: 'POST'});
                const data = await response.json();
                
                if (data.success) {
                    isConnected = false;
                    updateStatus(false, 'Desconectado');
                    addLog('info', 'Desconectado del puerto serial');
                }
            } catch (error) {
                addLog('error', `Error al desconectar: ${error.message}`);
            }
        }

        function updateServo(servoName, value) {
            const angle = parseInt(value);
            servoAngles[servoName] = angle;
            
            // Actualizar visualización
            document.getElementById(`${servoName}Value`).textContent = `${angle}°`;
            
            // Efecto visual
            const card = document.getElementById(`${servoName}Slider`).closest('.servo-card');
            card.classList.add('pulse-animation');
            setTimeout(() => card.classList.remove('pulse-animation'), 300);
            
            // Enviar comando si está conectado
            if (isConnected) {
                sendServoCommand({[servoName]: angle});
            }
        }

        async function sendServoCommand(data) {
            try {
                const response = await fetch('/api/servo', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (!result.success) {
                    addLog('error', result.message);
                }
            } catch (error) {
                addLog('error', `Error enviando comando: ${error.message}`);
            }
        }

        async function resetServos() {
            try {
                const response = await fetch('/api/reset');
                const data = await response.json();
                
                if (data.success) {
                    for (let i = 1; i <= 4; i++) {
                        document.getElementById(`servo${i}Slider`).value = 90;
                        document.getElementById(`servo${i}Value`).textContent = '90°';
                    }
                    servoAngles = {servo1: 90, servo2: 90, servo3: 90, servo4: 90};
                    addLog('info', 'Servos reseteados a 90°');
                } else {
                    addLog('error', data.message);
                }
            } catch (error) {
                addLog('error', `Error en reset: ${error.message}`);
            }
        }

        function updateStatus(connected, text) {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            
            statusDot.className = `status-dot ${connected ? 'status-connected' : 'status-disconnected'}`;
            statusText.textContent = text;
        }

        function addLog(type, message) {
            const logContainer = document.getElementById('logContainer');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${type}`;
            
            const icons = {
                success: '✅',
                error: '❌',
                info: '📘',
                command: '⚡'
            };
            
            logEntry.innerHTML = `${icons[type] || '📝'} [${timestamp}] ${message}`;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
            
            while (logContainer.children.length > 50) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }

        function updateServoValues() {
            for (let i = 1; i <= 4; i++) {
                const servoName = `servo${i}`;
                const slider = document.getElementById(`${servoName}Slider`);
                const valueDisplay = document.getElementById(`${servoName}Value`);
                
                if (slider && valueDisplay) {
                    const value = servoAngles[servoName] || 90;
                    slider.value = value;
                    valueDisplay.textContent = `${value}°`;
                }
            }
        }

        function savePreset() {
            const preset = JSON.stringify({
                servos: servoAngles,
                theme: currentSettings
            });
            localStorage.setItem('roboticArmPreset', preset);
            addLog('info', '💾 Preset (servo + tema) guardado');
        }

        function loadPreset() {
            const preset = localStorage.getItem('roboticArmPreset');
            if (preset) {
                try {
                    const data = JSON.parse(preset);
                    
                    // Cargar ángulos de servos
                    if (data.servos) {
                        servoAngles = data.servos;
                        updateServoValues();
                        
                        if (isConnected) {
                            sendServoCommand(servoAngles);
                        }
                    }
                    
                    // Cargar tema si existe
                    if (data.theme) {
                        currentSettings = data.theme;
                        loadSavedTheme();
                    }
                    
                    addLog('info', '📂 Preset completo cargado');
                } catch (error) {
                    addLog('error', 'Error cargando preset');
                }
            } else {
                addLog('info', 'No hay preset guardado');
            }
        }

        // Event listeners de Socket.IO
        socket.on('status_update', function(data) {
            updateStatus(data.connected, data.connected ? `Conectado a ${data.port}` : 'Desconectado');
            if (data.log) {
                data.log.forEach(entry => {
                    addLog(entry.type, entry.message);
                });
            }
        });

        socket.on('servo_update', function(data) {
            servoAngles = data.angles;
            updateServoValues();
            if (data.success) {
                addLog('command', `⚡ Comando ejecutado: ${JSON.stringify(data.angles)}`);
            }
        });

        socket.on('servo_reset', function(data) {
            servoAngles = data;
            updateServoValues();
            addLog('info', '🔄 Servos reseteados remotamente');
        });

        socket.on('background_updated', function(data) {
            if (data.image) {
                setBackgroundImage(data.image);
            } else {
                removeBackground();
            }
        });

        socket.on('theme_updated', function(data) {
            currentSettings = data;
            // Aplicar tema recibido de otros clientes
            loadSavedTheme();
        });

        // Obtener estado inicial
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                updateStatus(data.connected, data.connected ? `Conectado a ${data.port}` : 'Desconectado');
                servoAngles = data.servo_angles;
                updateServoValues();
                
                if (data.settings) {
                    currentSettings = data.settings;
                    if (data.settings.background_image) {
                        setBackgroundImage(data.settings.background_image);
                    }
                }
            });

        // Efectos de hover para las tarjetas
        document.addEventListener('mouseover', function(e) {
            if (e.target.closest('.servo-card')) {
                const card = e.target.closest('.servo-card');
                if (currentSettings.glow_effect) {
                    card.classList.add('glow-effect');
                }
            }
        });

        document.addEventListener('mouseout', function(e) {
            if (e.target.closest('.servo-card')) {
                const card = e.target.closest('.servo-card');
                card.classList.remove('glow-effect');
            }
        });
    </script>
</body>
</html>'''
    
    # Escribir archivo HTML mejorado
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("🚀 Iniciando servidor web mejorado...")
    print("🌐 Abre tu navegador en: http://localhost:5000")
    print("🎨 NUEVAS CARACTERÍSTICAS:")
    print("   ✨ Panel de personalización completo")
    print("   🖼️  Subida de imágenes de fondo")
    print("   🌈 6 temas predefinidos impresionantes")
    print("   🎨 Selector de colores en tiempo real")
    print("   ⚡ Efectos visuales avanzados")
    print("   💾 Guardado de temas personalizados")
    print("   📱 Partículas animadas configurables")
    print("   🔄 Sincronización en tiempo real entre usuarios")
    print("   🎯 Modo claro/oscuro")
    print("   🎲 Generador de colores aleatorios")
    print("\n" + "="*60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 Cerrando aplicación...")
        if controller.serial_connection and controller.serial_connection.is_open:
            controller.serial_connection.close()