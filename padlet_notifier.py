#!/usr/bin/env python3
import feedparser
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
import json
import os
import csv
import fcntl
import sys

# ============================
# CONFIGURACIÓN
# ============================

RSS_URL = "https://padlet.com/padlets/p1kdb8wyzxfghks/feed.xml?token=UmpWUFEzWmlRbVZrZWsxNU1TOVRiekJFYXpkcVpXbGhSR015WmxnMlFUTmhNMmRpZW1NclZVNVliakZIWXpWRVkxRTFlR3RsTHpOb00wSllPRFI2U2xBek5UWjZNbmc1UVV4b1ZrRkxURlJSTTJOWWVGazVSblpKU0RkUlNVZHliek5xVm1wWlREQlFSMEU5TFMxMWJIQlhNRmtyUTNsbWNFZHBVREY0YUZsUU5FdDNQVDA9LS00NGI2ZTYwYjM1YTUzMzQ2ZWUwMDFhMGZlZTZmNTYwOTEyYzgwNTZi"

PROFESORES_CSV = "/home/madrid/Padlet/profesores.csv"
ESTADO_FILE = "/home/madrid/Padlet/estado.json"
LOG_FILE = "/home/madrid/Padlet/log.txt"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
USERNAME = "isidro.hervas@gmail.com"
PASSWORD = "elspnkghzxjagvnb"


# ============================
# LOG
# ============================

def log(texto):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{fecha} {texto}\n")
    print(f"{fecha} {texto}")


# ============================
# CARGA PROFESORES
# ============================

def cargar_profesores():
    profesores = {}
    with open(PROFESORES_CSV, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            codigo = fila["codigo"].strip()
            correo = fila["correo"].strip()
            if codigo not in profesores:
                profesores[codigo] = []
            profesores[codigo].append(correo)
    return profesores


# ============================
# ENVÍO MAIL (HTML)
# ============================

def enviar_email(destinatarios, codigo_clase, titulo, contenido):
    msg = EmailMessage()
    msg["From"] = f"AVISO DE NUEVA TUTORÍA"
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = f"📝 Nueva tutoría en grupo {codigo_clase}"

    sep = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    html = f"""
<b>NOVEDAD EN EL PADLET</b><br>
{sep}<br>
📚 <b>Grupo:</b> <span style="color:blue">{codigo_clase}</span><br>
{sep}<br><br>

📅 <b><span style="color:red">{titulo}</span></b><br>
👤 <b><span style="color:blue">{contenido}</span></b><br>
<br>
{sep}<br><br>

<p style="font-weight:bold; color:darkred;">
⚠️ POR FAVOR, NO OLVIDÉIS RELLENAR LA FICHA DE ENTREVISTA QUE SE ENCUENTRA EN EL CLOUD ⚠️
</p>
"""

    msg.set_content(html)
    msg.add_alternative(f"<html><body>{html}</body></html>", subtype='html')

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.send_message(msg)

    log(f"📧 Email enviado a {codigo_clase}: {destinatarios}")


# ============================
# PROCESO
# ============================

def procesar():
    log("▶️ Iniciando comprobación…")

    profesores = cargar_profesores()
    log(f"✔️ Profesores cargados: {profesores}")

    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            estado = json.load(f)
            ultima_fecha_str = estado.get("ultima_fecha")
            if ultima_fecha_str:
                ultima_fecha = datetime.fromisoformat(ultima_fecha_str)
            else:
                ultima_fecha = datetime.min.replace(tzinfo=timezone.utc)
    else:
        ultima_fecha = datetime.min.replace(tzinfo=timezone.utc)

    log(f"✔️ Última fecha procesada: {ultima_fecha}")

    feed = feedparser.parse(RSS_URL)
    log(f"✔️ Entradas RSS detectadas: {len(feed.entries)}")

    nueva_fecha_max = ultima_fecha

    for entry in feed.entries:
        titulo = entry.get("title", "")
        descripcion_html = entry.get("summary", "")

        try:
            pubDate = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except:
            continue

        if pubDate <= ultima_fecha:
            continue

        # limpiar HTML
        descripcion = (
            descripcion_html.replace("<p>", "")
            .replace("</p>", "\n")
            .replace("<br>", "\n")
            .replace("<br/>", "\n")
            .strip()
        )

        lineas = descripcion.splitlines()

        for codigo_clase, correos in profesores.items():
            contenido_clase = []
            for l in lineas:
                linea = l.strip()
                if linea.startswith(codigo_clase):
                    linea_sin = linea[len(codigo_clase):].strip(" :-")
                    contenido_clase.append(linea_sin)

            if not contenido_clase:
                continue

            mensaje_final = "\n".join(contenido_clase)
            enviar_email(correos, codigo_clase, titulo, mensaje_final)

        if pubDate > nueva_fecha_max:
            nueva_fecha_max = pubDate

    if nueva_fecha_max > ultima_fecha:
        with open(ESTADO_FILE, "w", encoding="utf-8") as f:
            json.dump({"ultima_fecha": nueva_fecha_max.isoformat()}, f)
        log("✔️ Actualizada última fecha procesada.")

    log("✔️ Script completado.")


# ============================
# LOCK PARA EVITAR DOBLE EJECUCIÓN
# ============================

lock_file_path = '/tmp/padlet_notifier.lock'
lock_file = open(lock_file_path, 'w')

try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("⚠️ El script ya está en ejecución. Saliendo.")
    sys.exit(0)


if __name__ == "__main__":
    procesar()







































