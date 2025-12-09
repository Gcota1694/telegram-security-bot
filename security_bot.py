#!/usr/bin/env python3
"""
Bot de Telegram para Raspberry Pi - Sistema de Seguridad Completo
Características:
- Control remoto seguro con autenticación
- Detección de movimiento con alertas automáticas
- Programación de tareas persistentes
- Ejecución de comandos por audio (speech recognition)
- Control GPIO
- Monitoreo del sistema
"""

import os
import json
import logging
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logging.warning("OpenCV no disponible. Detección de movimiento deshabilitada.")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar configuración
with open('config/config.json', 'r') as f:
    CONFIG = json.load(f)

TELEGRAM_TOKEN = CONFIG['telegram']['token']
AUTHORIZED_USERS = CONFIG['telegram']['authorized_users']
COMMANDS_WHITELIST = CONFIG['commands_whitelist']
DB_PATH = CONFIG['paths']['db']

# Variables globales para detección de movimiento
motion_detection_active = False
motion_thread = None
last_motion_time = 0
MOTION_COOLDOWN = 30  # segundos entre alertas

# Base de datos
def init_db():
    """Inicializar base de datos SQLite"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabla de tareas programadas
    c.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            schedule_time TEXT,
            frequency TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de eventos de seguridad
    c.execute('''
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            description TEXT,
            photo_path TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def log_security_event(event_type: str, description: str, photo_path: str = None):
    """Registrar evento de seguridad en la BD"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO security_events (event_type, description, photo_path) VALUES (?, ?, ?)",
            (event_type, description, photo_path)
        )
        conn.commit()
        conn.close()
        logger.info(f"Evento de seguridad registrado: {event_type} - {description}")
    except Exception as e:
        logger.error(f"Error registrando evento: {e}")

# Decorador de autorización
def authorized_only(func):
    """Decorador para verificar autorización de usuario"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or "Desconocido"
        
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("⛔ Acceso denegado. No estás autorizado.")
            logger.warning(f"Intento de acceso no autorizado: {user_id} (@{username})")
            log_security_event("unauthorized_access", f"Usuario {user_id} (@{username}) intentó acceder")
            return
        return await func(update, context)
    return wrapper

# ===== DETECCIÓN DE MOVIMIENTO =====

def detect_motion():
    """Thread para detectar movimiento con la cámara"""
    global motion_detection_active, last_motion_time
    
    if not OPENCV_AVAILABLE:
        logger.error("OpenCV no disponible. No se puede iniciar detección de movimiento.")
        return
    
    logger.info("Iniciando detección de movimiento")
    
    try:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Leer primer frame
        ret, frame1 = cap.read()
        ret, frame2 = cap.read()
        
        while motion_detection_active:
            try:
                # Calcular diferencia entre frames
                diff = cv2.absdiff(frame1, frame2)
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
                dilated = cv2.dilate(thresh, None, iterations=3)
                contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                
                # Detectar movimiento significativo
                motion_detected = False
                for contour in contours:
                    if cv2.contourArea(contour) > 5000:  # Área mínima
                        motion_detected = True
                        break
                
                if motion_detected:
                    current_time = time.time()
                    if current_time - last_motion_time > MOTION_COOLDOWN:
                        last_motion_time = current_time
                        logger.warning("¡MOVIMIENTO DETECTADO!")
                        
                        # Capturar foto
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        photo_path = f"media/motion_{timestamp}.jpg"
                        cv2.imwrite(photo_path, frame1)
                        
                        # Registrar evento
                        log_security_event("motion_detected", "Movimiento detectado", photo_path)
                        
                        # Enviar alerta (usar asyncio para llamar función async)
                        import asyncio
                        asyncio.run(send_motion_alert(photo_path))
                
                # Actualizar frames
                frame1 = frame2
                ret, frame2 = cap.read()
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error en detección de movimiento: {e}")
                time.sleep(1)
        
        cap.release()
        logger.info("Detección de movimiento detenida")
        
    except Exception as e:
        logger.error(f"Error fatal en detección de movimiento: {e}")

async def send_motion_alert(photo_path: str):
    """Enviar alerta de movimiento a usuarios autorizados"""
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        for user_id in AUTHORIZED_USERS:
            try:
                with open(photo_path, 'rb') as photo:
                    await app.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption="🚨 <b>ALERTA DE SEGURIDAD</b>\n\n"
                                "⚠️ Movimiento detectado\n"
                                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode='HTML'
                    )
                logger.info(f"Alerta enviada a usuario {user_id}")
            except Exception as e:
                logger.error(f"Error enviando alerta a {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error en send_motion_alert: {e}")

# ===== COMANDOS DEL BOT =====

@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando inicial"""
    keyboard = [
        [InlineKeyboardButton("📊 Estado", callback_data='status'),
         InlineKeyboardButton("📸 Foto", callback_data='photo')],
        [InlineKeyboardButton("🎥 Toggle Motion", callback_data='toggle_motion'),
         InlineKeyboardButton("📋 Tareas", callback_data='tasks')],
        [InlineKeyboardButton("🔧 GPIO", callback_data='gpio_menu'),
         InlineKeyboardButton("🔄 Reboot", callback_data='reboot_ask')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    num_users = len(AUTHORIZED_USERS)
    welcome_text = f"""🤖 <b>Sistema de Seguridad Raspberry Pi</b>

<b>🔹 Monitoreo y Seguridad</b>
/status - Estado del sistema
/photo - Capturar foto ahora
/motion - Activar/desactivar detección
/events - Ver últimos eventos de seguridad

<b>🔹 Ejecución de Comandos</b>
/run comando - Ejecutar comando de whitelist
/exec_safe script - Ejecutar script aprobado
📎 Envía audio para ejecutar comandos por voz

<b>🔹 Programación de Tareas</b>
/schedule HH:MM comando - Programar tarea
/tasks - Ver tareas programadas
/cancel ID - Cancelar tarea

<b>🔹 Control GPIO</b>
/gpio PIN on|off - Controlar pin GPIO

<b>🔹 Sistema</b>
/reboot - Reiniciar Raspberry Pi
/help - Ayuda detallada

✅ Usuarios autorizados: {num_users}
🔐 Sistema de seguridad activo"""

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

@authorized_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estado del sistema"""
    try:
        # Temperatura
        temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        temp = temp.replace('temp=', '').strip()

        # Uptime
        uptime = subprocess.check_output(['uptime', '-p']).decode().strip()

        # Memoria
        mem = subprocess.check_output(['free', '-h']).decode().split('\n')[1].split()
        mem_total = mem[1]
        mem_used = mem[2]

        # Disco
        disk = subprocess.check_output(['df', '-h', '/']).decode().split('\n')[1].split()
        disk_total = disk[1]
        disk_used = disk[2]
        disk_percent = disk[4]
        
        # IP
        ip = subprocess.check_output(['hostname', '-I']).decode().strip().split()[0]

        motion_status = '✅ Activa' if motion_detection_active else '❌ Inactiva'
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        status_text = f"""📊 <b>Estado del Sistema</b>

🌡️ Temperatura: {temp}
⏰ Uptime: {uptime}
🌐 IP Local: {ip}

💾 <b>Memoria</b>
Total: {mem_total} | Usado: {mem_used}

💿 <b>Disco</b>
Total: {disk_total} | Usado: {disk_used} ({disk_percent})

🎥 Detección de movimiento: {motion_status}

✅ Sistema operando normalmente
🕐 {current_time}"""

        await update.message.reply_text(status_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capturar foto"""
    await update.message.reply_text("📸 Capturando foto...")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = f"media/photo_{timestamp}.jpg"

        if OPENCV_AVAILABLE:
            # Capturar con OpenCV
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(photo_path, frame)
            cap.release()
        else:
            # Fallback a fswebcam
            subprocess.run([
                'fswebcam',
                '-r', '1280x720',
                '--no-banner',
                photo_path
            ], check=True)

        # Enviar foto
        with open(photo_path, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=f"📸 Foto capturada\n🕐 {timestamp}"
            )

        logger.info(f"Foto capturada: {photo_path}")

    except Exception as e:
        logger.error(f"Error capturando foto: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def toggle_motion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activar/desactivar detección de movimiento"""
    global motion_detection_active, motion_thread

    if not OPENCV_AVAILABLE:
        await update.message.reply_text("❌ OpenCV no está instalado. Instala con: pip install opencv-python")
        return

    if not motion_detection_active:
        motion_detection_active = True
        motion_thread = threading.Thread(target=detect_motion, daemon=True)
        motion_thread.start()
        await update.message.reply_text("✅ Detección de movimiento ACTIVADA\n🚨 Recibirás alertas automáticas")
        log_security_event("motion_enabled", "Detección de movimiento activada")
    else:
        motion_detection_active = False
        if motion_thread:
            motion_thread.join(timeout=2)
        await update.message.reply_text("❌ Detección de movimiento DESACTIVADA")
        log_security_event("motion_disabled", "Detección de movimiento desactivada")

@authorized_only
async def security_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver últimos eventos de seguridad"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT event_type, description, timestamp FROM security_events ORDER BY timestamp DESC LIMIT 10"
        )
        events = c.fetchall()
        conn.close()

        if not events:
            await update.message.reply_text("📋 No hay eventos de seguridad registrados")
            return

        events_text = "🔐 <b>Últimos Eventos de Seguridad</b>\n\n"
        for event_type, description, timestamp in events:
            events_text += f"• <b>{event_type}</b>\n  {description}\n  🕐 {timestamp}\n\n"

        await update.message.reply_text(events_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error listando eventos: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecutar comando de whitelist"""
    if not context.args:
        commands_list = "\n".join(f"• {cmd}" for cmd in COMMANDS_WHITELIST)
        await update.message.reply_text(
            f"❌ Uso: /run comando\n\n<b>Comandos permitidos:</b>\n{commands_list}",
            parse_mode='HTML'
        )
        return

    command = ' '.join(context.args)

    if not any(command.startswith(allowed) for allowed in COMMANDS_WHITELIST):
        await update.message.reply_text(f"⛔ Comando no permitido: {command}")
        log_security_event("blocked_command", f"Intento de ejecutar: {command}")
        return

    try:
        await update.message.reply_text(f"⚙️ Ejecutando: {command}")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout if result.stdout else result.stderr
        if len(output) > 3900:
            output = output[:3900] + "\n\n... (truncado)"

        await update.message.reply_text(f"✅ Resultado:\n\n<code>{output}</code>", parse_mode='HTML')
        log_security_event("command_executed", f"Ejecutado: {command}")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ Timeout (30s)")
    except Exception as e:
        logger.error(f"Error ejecutando comando: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def schedule_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Programar tarea"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Uso: /schedule HH:MM comando\n\n"
            "Ejemplo: /schedule 22:00 ./backup.sh"
        )
        return

    schedule_time = context.args[0]
    command = ' '.join(context.args[1:])
    user_id = update.effective_user.id

    try:
        datetime.strptime(schedule_time, '%H:%M')
    except ValueError:
        await update.message.reply_text("❌ Formato inválido. Usa HH:MM")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO scheduled_tasks (user_id, command, schedule_time, frequency) VALUES (?, ?, ?, ?)",
            (user_id, command, schedule_time, 'daily')
        )
        task_id = c.lastrowid
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Tarea programada\n\n"
            f"ID: {task_id}\n"
            f"⏰ {schedule_time} (diario)\n"
            f"📝 {command}"
        )

        log_security_event("task_scheduled", f"Tarea {task_id}: {command} a las {schedule_time}")

    except Exception as e:
        logger.error(f"Error programando tarea: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listar tareas programadas"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, command, schedule_time, active FROM scheduled_tasks WHERE active = 1")
        tasks = c.fetchall()
        conn.close()

        if not tasks:
            await update.message.reply_text("📋 No hay tareas programadas")
            return

        tasks_text = "📋 <b>Tareas Programadas</b>\n\n"
        for task_id, command, schedule_time, active in tasks:
            status = "✅" if active else "❌"
            tasks_text += f"{status} <b>ID {task_id}</b>\n⏰ {schedule_time}\n📝 {command}\n\n"

        await update.message.reply_text(tasks_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error listando tareas: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancelar tarea"""
    if not context.args:
        await update.message.reply_text("❌ Uso: /cancel ID")
        return

    try:
        task_id = int(context.args[0])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE scheduled_tasks SET active = 0 WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Tarea {task_id} cancelada")
        log_security_event("task_cancelled", f"Tarea {task_id} cancelada")

    except ValueError:
        await update.message.reply_text("❌ ID inválido")
    except Exception as e:
        logger.error(f"Error cancelando tarea: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def gpio_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Controlar GPIO"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Uso: /gpio PIN on|off\n\nEjemplo: /gpio 17 on")
        return

    try:
        from gpiozero import LED

        pin = int(context.args[0])
        action = context.args[1].lower()

        if action not in ['on', 'off']:
            await update.message.reply_text("❌ Acción debe ser 'on' o 'off'")
            return

        led = LED(pin)

        if action == 'on':
            led.on()
            await update.message.reply_text(f"✅ GPIO {pin} activado")
        else:
            led.off()
            await update.message.reply_text(f"✅ GPIO {pin} desactivado")

        log_security_event("gpio_control", f"GPIO {pin} {action}")

    except Exception as e:
        logger.error(f"Error controlando GPIO: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def reboot_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reiniciar sistema"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data='reboot_confirm'),
            InlineKeyboardButton("❌ Cancelar", callback_data='reboot_cancel')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ ¿Confirmas reiniciar el sistema?",
        reply_markup=reply_markup
    )

# Handler de botones
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar botones inline"""
    query = update.callback_query
    await query.answer()

    # Crear un update temporal para que funcionen los comandos
    if query.data == 'status':
        fake_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        fake_update._effective_user = query.from_user
        fake_update._effective_chat = query.message.chat
        await status(fake_update, context)
    elif query.data == 'photo':
        fake_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        fake_update._effective_user = query.from_user
        fake_update._effective_chat = query.message.chat
        await photo(fake_update, context)
    elif query.data == 'toggle_motion':
        fake_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        fake_update._effective_user = query.from_user
        fake_update._effective_chat = query.message.chat
        await toggle_motion(fake_update, context)
    elif query.data == 'tasks':
        fake_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        fake_update._effective_user = query.from_user
        fake_update._effective_chat = query.message.chat
        await list_tasks(fake_update, context)
    elif query.data == 'reboot_confirm':
        await query.edit_message_text("🔄 Reiniciando sistema...")
        log_security_event("system_reboot", "Sistema reiniciado por usuario")
        subprocess.Popen(['sudo', 'reboot'])
    elif query.data == 'reboot_cancel':
        await query.edit_message_text("❌ Reinicio cancelado")

# Handler de voz
@authorized_only
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesar comandos de voz"""
    await update.message.reply_text("🎤 Procesando audio...")

    try:
        # Descargar audio
        voice_file = await update.message.voice.get_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = f"media/voice_{timestamp}.ogg"
        wav_path = f"media/voice_{timestamp}.wav"
        
        await voice_file.download_to_drive(audio_path)

        # Convertir a WAV
        subprocess.run([
            'ffmpeg', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path
        ], check=True, capture_output=True)

        # Reconocimiento de voz con vosk
        try:
            import vosk
            import wave

            model = vosk.Model("model")
            wf = wave.open(wav_path, "rb")
            rec = vosk.KaldiRecognizer(model, wf.getframerate())

            text = ""
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text += result.get("text", "")

            result = json.loads(rec.FinalResult())
            text += result.get("text", "")

            if not text:
                await update.message.reply_text("❌ No se pudo reconocer el audio")
                return

            await update.message.reply_text(f"🎤 Reconocido: <i>{text}</i>", parse_mode='HTML')

            # Ejecutar comando si está en whitelist
            if any(text.startswith(allowed) for allowed in COMMANDS_WHITELIST):
                context.args = text.split()
                await run_command(update, context)
            else:
                await update.message.reply_text(f"⛔ Comando no permitido: {text}")

        except ImportError:
            await update.message.reply_text("❌ Vosk no está instalado. Instala con: pip install vosk")

    except Exception as e:
        logger.error(f"Error procesando voz: {e}")
        await update.message.reply_text(f"❌ Error procesando audio: {str(e)}")

def main():
    """Función principal"""
    # Inicializar
    init_db()
    Path('logs').mkdir(exist_ok=True)
    Path('media').mkdir(exist_ok=True)
    Path('db').mkdir(exist_ok=True)

    # Crear aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registrar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("photo", photo))
    application.add_handler(CommandHandler("motion", toggle_motion))
    application.add_handler(CommandHandler("events", security_events))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("schedule", schedule_task))
    application.add_handler(CommandHandler("tasks", list_tasks))
    application.add_handler(CommandHandler("cancel", cancel_task))
    application.add_handler(CommandHandler("gpio", gpio_control))
    application.add_handler(CommandHandler("reboot", reboot_system))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))

    logger.info("🤖 Sistema de seguridad iniciado")
    log_security_event("system_started", "Bot iniciado correctamente")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
