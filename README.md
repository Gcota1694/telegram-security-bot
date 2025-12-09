# 🤖 Telegram Security Bot para Raspberry Pi

Sistema de seguridad completo controlado por Telegram con detección de movimiento, control GPIO y ejecución remota de comandos.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red.svg)

## ✨ Características

- 🔐 **Seguridad**: Autenticación de usuarios autorizados con registro de intentos de acceso
- 📸 **Cámara**: Captura de fotos bajo demanda
- 🎥 **Detección de movimiento**: Alertas automáticas con foto cuando se detecta movimiento
- 🚨 **Alertas en tiempo real**: Notificaciones instantáneas vía Telegram
- 🎙️ **Control por voz**: Ejecuta comandos mediante mensajes de audio
- ⚡ **GPIO**: Control de pines GPIO (LEDs, buzzers, sensores)
- 📊 **Monitoreo del sistema**: Temperatura, memoria, disco, uptime, IP local
- ⏰ **Tareas programadas**: Automatización de comandos con programación persistente
- 📝 **Registro de eventos**: Base de datos SQLite con historial de seguridad
- 🛡️ **Whitelist de comandos**: Solo comandos aprobados pueden ejecutarse

## 🛠️ Requisitos

### Hardware
- Raspberry Pi (cualquier modelo con GPIO)
- Cámara USB o módulo de cámara Raspberry Pi
- (Opcional) LEDs, buzzer, sensor PIR para GPIO

### Software
- Raspberry Pi OS (Raspbian)
- Python 3.7 o superior
- Bot de Telegram (token de @BotFather)

## 📦 Instalación

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/Gcota1694/telegram-security-bot.git
cd telegram-security-bot
```

### 2️⃣ Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4️⃣ Configurar el bot

#### Obtener token de Telegram:
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Envía `/newbot` y sigue las instrucciones
3. Copia el token que te da

#### Obtener tu User ID:
1. Habla con [@userinfobot](https://t.me/userinfobot)
2. Copia tu ID numérico

#### Configurar el archivo:
```bash
cp config/config.json.example config/config.json
nano config/config.json
```

Edita estos valores:
```json
{
  "telegram": {
    "token": "TU_TOKEN_AQUI",
    "authorized_users": [TU_USER_ID_AQUI]
  }
}
```

### 5️⃣ Ejecutar el bot

```bash
python3 security_bot.py
```

## 🚀 Ejecutar como servicio (Opcional pero recomendado)

Para que el bot se inicie automáticamente al arrancar:

### Crear servicio systemd

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Añade este contenido (ajusta las rutas según tu instalación):

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
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Habilitar y arrancar el servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### Verificar estado

```bash
sudo systemctl status telegram-bot
```

### Ver logs en tiempo real

```bash
sudo journalctl -u telegram-bot -f
```

## 📱 Comandos del Bot

### 🔹 Monitoreo y Seguridad

| Comando | Descripción |
|---------|-------------|
| `/start` | Menú principal con botones interactivos |
| `/status` | Estado completo del sistema (CPU, RAM, disco, temperatura, IP) |
| `/photo` | Capturar foto inmediatamente |
| `/motion` | Activar/desactivar detección de movimiento |
| `/events` | Ver últimos 10 eventos de seguridad |

### 🔹 Ejecución de Comandos

| Comando | Descripción |
|---------|-------------|
| `/run [comando]` | Ejecutar comando de whitelist |
| `🎤 Enviar audio` | Ejecutar comandos por reconocimiento de voz |

**Ejemplo:**
```
/run df -h
/run uptime
```

### 🔹 Programación de Tareas

| Comando | Descripción |
|---------|-------------|
| `/schedule HH:MM comando` | Programar tarea diaria |
| `/tasks` | Listar tareas programadas activas |
| `/cancel ID` | Cancelar tarea por ID |

**Ejemplo:**
```
/schedule 22:00 ./scripts/backup.sh
/schedule 06:00 systemctl status
```

### 🔹 Control GPIO

| Comando | Descripción |
|---------|-------------|
| `/gpio PIN on\|off` | Controlar pin GPIO específico |

**Ejemplo:**
```
/gpio 17 on    # Encender LED en GPIO 17
/gpio 17 off   # Apagar LED en GPIO 17
```

### 🔹 Sistema

| Comando | Descripción |
|---------|-------------|
| `/reboot` | Reiniciar Raspberry Pi (requiere confirmación) |

## 🔒 Seguridad

El bot implementa múltiples capas de seguridad:

### ✅ Autenticación
- Solo usuarios con ID en `authorized_users` pueden usar el bot
- Todos los intentos de acceso no autorizado se registran

### ✅ Whitelist de Comandos
Solo los comandos en `commands_whitelist` pueden ejecutarse:
```json
"commands_whitelist": [
  "ls",
  "df -h",
  "free -h",
  "uptime",
  "vcgencmd measure_temp",
  "systemctl status",
  "pm2 list",
  "git status"
]
```

### ✅ Registro de Eventos
Todos los eventos se guardan en `db/bot.db`:
- Accesos no autorizados
- Comandos ejecutados
- Detección de movimiento
- Activación/desactivación de funciones
- Reinicio del sistema

### ✅ Timeout de Comandos
Los comandos tienen un timeout de 30 segundos para prevenir ejecuciones indefinidas.

## 📁 Estructura del Proyecto

```
telegram-security-bot/
├── config/
│   ├── config.json              # Configuración principal (NO subir a Git)
│   └── config.json.example      # Plantilla de configuración
├── db/
│   └── bot.db                   # Base de datos SQLite
├── logs/
│   └── bot.log                  # Logs del sistema
├── media/
│   ├── photo_*.jpg              # Fotos capturadas manualmente
│   └── motion_*.jpg             # Fotos de detección de movimiento
├── model/
│   └── vosk-model/              # Modelo de reconocimiento de voz (descargar aparte)
├── scripts/
│   └── backup.sh                # Scripts personalizados
├── .gitignore                   # Archivos ignorados por Git
├── README.md                    # Este archivo
├── requirements.txt             # Dependencias Python
└── security_bot.py              # Script principal del bot
```

## 🎙️ Configurar Reconocimiento de Voz (Opcional)

Para usar comandos por voz, descarga un modelo de Vosk:

```bash
cd model
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip
mv vosk-model-small-es-0.42 vosk-model
```

O usa el modelo en inglés:
```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
```

## 🔧 Configuración Avanzada

### Configurar Pines GPIO

Edita `config/config.json`:

```json
"gpio": {
  "enabled": true,
  "pins": {
    "led": 17,           # Pin para LED de estado
    "buzzer": 27,        # Pin para buzzer de alarma
    "motion_sensor": 4   # Pin para sensor PIR
  }
}
```

### Ajustar Sensibilidad de Detección de Movimiento

En `security_bot.py`, línea ~140:

```python
if cv2.contourArea(contour) > 5000:  # Ajusta este valor
```

- Valor más bajo = más sensible
- Valor más alto = menos sensible

### Cambiar Cooldown de Alertas

En `security_bot.py`, línea ~60:

```python
MOTION_COOLDOWN = 30  # segundos entre alertas
```

## 🐛 Troubleshooting

### ❌ Error: "OpenCV no disponible"

```bash
pip install opencv-python
```

Si sigue fallando en Raspberry Pi:
```bash
sudo apt-get install python3-opencv
```

### ❌ Error: "No module named 'telegram'"

```bash
pip install python-telegram-bot==20.7
```

### ❌ Cámara no detectada

Verificar dispositivos de cámara:
```bash
ls /dev/video*
```

Si no aparece, habilitar cámara:
```bash
sudo raspi-config
# Interfacing Options → Camera → Enable
sudo reboot
```

### ❌ GPIO no funciona

Instalar gpiozero:
```bash
pip install gpiozero
```

Verificar permisos:
```bash
sudo usermod -a -G gpio $USER
```

### ❌ El bot no responde

1. Verificar que el bot está corriendo:
```bash
ps aux | grep security_bot
```

2. Ver logs:
```bash
tail -f logs/bot.log
```

3. Verificar token en `config/config.json`

### ❌ Error de permisos al ejecutar comandos

Algunos comandos requieren `sudo`. Añádelos al archivo sudoers:
```bash
sudo visudo
```

Añade al final:
```
pi ALL=(ALL) NOPASSWD: /sbin/reboot
```

## 📊 Base de Datos

El bot usa SQLite para persistencia. Tablas:

### `scheduled_tasks`
- `id`: ID único de la tarea
- `user_id`: ID del usuario que la creó
- `command`: Comando a ejecutar
- `schedule_time`: Hora de ejecución (HH:MM)
- `frequency`: Frecuencia (daily)
- `active`: Estado (1=activa, 0=cancelada)
- `created_at`: Fecha de creación

### `security_events`
- `id`: ID único del evento
- `event_type`: Tipo de evento
- `description`: Descripción
- `photo_path`: Ruta de foto (si aplica)
- `timestamp`: Fecha y hora

### Ver base de datos manualmente:

```bash
sqlite3 db/bot.db
.tables
SELECT * FROM security_events ORDER BY timestamp DESC LIMIT 5;
.quit
```

## 🔄 Actualizar el Bot

```bash
cd telegram-security-bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart telegram-bot
```

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 To-Do / Mejoras Futuras

- [ ] Integración con Home Assistant
- [ ] Soporte para múltiples cámaras
- [ ] Dashboard web con Flask
- [ ] Notificaciones por email
- [ ] Reconocimiento facial
- [ ] Integración con Alexa/Google Home
- [ ] Modo "vacaciones" con simulación de presencia
- [ ] Backup automático a la nube
- [ ] App móvil nativa
- [ ] Soporte para sensores de temperatura/humedad

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👨‍💻 Autor

**Gabriel Cota**
- GitHub: [@Gcota1694](https://github.com/Gcota1694)
- Email: al22760043@ite.edu.mx

## 🙏 Agradecimientos

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Framework de Telegram
- [OpenCV](https://opencv.org/) - Visión por computadora
- [Vosk](https://alphacephei.com/vosk/) - Reconocimiento de voz offline
- [gpiozero](https://gpiozero.readthedocs.io/) - Control GPIO simplificado

## 📚 Referencias

- [Documentación python-telegram-bot](https://docs.python-telegram-bot.org/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [OpenCV Tutorials](https://docs.opencv.org/master/d9/df8/tutorial_root.html)

---

<div align="center">

**⭐ Si te gustó este proyecto, dale una estrella! ⭐**

Made with ❤️ for Raspberry Pi

</div>
