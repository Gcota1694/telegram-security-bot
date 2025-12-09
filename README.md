# 🤖 Telegram Security Bot para Raspberry Pi

Sistema de seguridad completo controlado por Telegram con detección de movimiento, control GPIO y ejecución remota de comandos.

## ✨ Características

- 🔐 **Seguridad**: Autenticación de usuarios autorizados
- 📸 **Cámara**: Captura de fotos y detección de movimiento
- 🚨 **Alertas**: Notificaciones automáticas de eventos
- 🎙️ **Control por voz**: Ejecuta comandos mediante audio
- ⚡ **GPIO**: Control de pines GPIO (LEDs, buzzers, sensores)
- 📊 **Monitoreo**: Estado del sistema (temperatura, memoria, disco)
- ⏰ **Tareas programadas**: Automatización de comandos
- 📝 **Logs**: Registro de eventos de seguridad

## 🛠️ Requisitos

- Raspberry Pi (cualquier modelo con GPIO)
- Cámara USB o módulo de cámara
- Python 3.7+
- Bot de Telegram (obtén token de @BotFather)

## 📦 Instalación

### 1. Clonar repositorio
```bash
git clone https://github.com/TU_USUARIO/telegram-security-bot.git
cd telegram-security-bot
```

### 2. Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar
Copia el archivo de configuración de ejemplo:
```bash
cp config/config.json.example config/config.json
nano config/config.json
```

Edita y añade:
- Tu token de Telegram Bot
- Tu User ID de Telegram (obtén con @userinfobot)

### 5. Ejecutar
```bash
python3 security_bot.py
```

### 6. Ejecutar como servicio (opcional)
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Añade:
```ini
[Unit]
Description=Telegram Security Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/telegram-security-bot
ExecStart=/home/pi/telegram-security-bot/venv/bin/python /home/pi/telegram-security-bot/security_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Habilitar servicio:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 📱 Comandos del Bot

### Monitoreo
- `/start` - Menú principal
- `/status` - Estado del sistema
- `/photo` - Capturar foto
- `/motion` - Activar/desactivar detección de movimiento
- `/events` - Ver últimos eventos de seguridad

### Ejecución
- `/run [comando]` - Ejecutar comando de whitelist
- Envía **audio** para ejecutar comandos por voz

### Tareas
- `/schedule HH:MM comando` - Programar tarea
- `/tasks` - Ver tareas programadas
- `/cancel ID` - Cancelar tarea

### GPIO
- `/gpio PIN on|off` - Controlar pin GPIO

### Sistema
- `/reboot` - Reiniciar Raspberry Pi

## 🔒 Seguridad

- ✅ Solo usuarios autorizados pueden ejecutar comandos
- ✅ Whitelist de comandos permitidos
- ✅ Registro de todos los eventos de seguridad
- ✅ Logs de intentos de acceso no autorizados

## 📁 Estructura del Proyecto
```
telegram-security-bot/
├── config/
│   └── config.json          # Configuración (NO subir a Git)
├── db/
│   └── bot.db              # Base de datos SQLite
├── logs/
│   └── bot.log             # Logs del sistema
├── media/
│   └── *.jpg               # Fotos capturadas
├── model/
│   └── vosk-model/         # Modelo de reconocimiento de voz
├── scripts/
│   └── backup.sh           # Scripts personalizados
├── security_bot.py         # Script principal
└── requirements.txt        # Dependencias Python
```

## 🐛 Troubleshooting

### Error: "OpenCV no disponible"
```bash
pip install opencv-python
```

### Error: "No module named 'telegram'"
```bash
pip install python-telegram-bot
```

### Cámara no detectada
```bash
ls /dev/video*
```

## 📄 Licencia

MIT License

## 👨‍💻 Autor

Tu Nombre - [@tu_usuario](https://github.com/tu_usuario)

## 🙏 Agradecimientos

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [OpenCV](https://opencv.org/)
- [Vosk Speech Recognition](https://alphacephei.com/vosk/)
