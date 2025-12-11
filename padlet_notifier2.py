#!/usr/bin/env python3
import csv
import smtplib
from email.message import EmailMessage
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import json
import os
import re

# ---------------- CONFIGURACIÓN ----------------
RSS_URL = "https://padlet.com/padlets/nd312z2olor6ikiy/feed.xml?token=T1ZCMGRrcEhjMU5QZEdaa1IyVTFhbVJPV25jeVZHWkVObmxUTlcwemF6Z3pNSEZDZVhCelVVcFJPV05hWmxJeVVsVlpRUzlWZFdSbFVrNXRkbVYyVXpBMGVGZERjMWR6ZVVsU2JWQnpVek01TjNoTWJsTnNSV1ZrYm1sT2JuTjJValI2Vkdka1NUUkplRzg5TFMwNGRGSklWMU51V0ZFeGRsQlRSemt2Y0hSc2VFcDNQVDA9LS04ZWMzMTE4ZGU3N2NiZGU3NjU2Y2FlOTIwNjM2YzliMDZkYTc4ZGUy"

PROFESORES_CSV = "/home/madrid/Padlet/profesores.csv"
ESTADO_FILE = "/home/madrid/Padlet/estado2.json"
LOG_FILE = "/home/madrid/Padlet/log2.txt"
LOCK_FILE = "/home/madrid/Padlet/lock2.lock"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
USERNAME = "isidro.hervas@gmail.com"
PASSWORD = "elspnkghzxjagvnb"


# ---------------- FUNCIONES ----------------
def log(msg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now} {msg}\n")
    print(f"{now} {msg}")


def cargar_profesores():
    profesores = {}
    with open(PROFESORES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = row['codigo'].strip()
            correos = [c.strip() for c in row['correo'].split(',')]
            profesores[codigo] = correos
    return profesores


def enviar_email(destinatarios, codigo_clase, titulo, contenido_html):
    msg = EmailMessage()
    msg["From"] = f"AVISOS EXPULSIONES - {codigo_clase}"
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = f"📚 AVISO EXPULSIONES ({codigo_clase})"

    # HTML formateado bonito
    html = f"""
    <html>
    <body style="font-family: Arial; font-size: 15px;">
        <h2>📚 Aviso de Expulsión - Grupo {codigo_clase}</h2>

        <p><b style="color:red;">📅 Fecha / Publicación:</b>
           <span style="color:blue;">{titulo}</span></p>

        <p><b style="color:red;">👤 Alumno/a:</b>
           <span style="color:blue;">{contenido_html}</span></p>

        <br>

        <p style="font-weight:bold; color:darkred;">
            ⚠️ POR FAVOR, NO OLVIDÉIS MANDARLE TRABAJO POR EL AULA VIRTUAL ⚠️
        </p>
    </body>
    </html>
    """

    msg.set_content("Este mensaje requiere un cliente con HTML.")
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(USERNAME, PASSWORD)
        server.send_message(msg)

    log(f"📧 Email enviado a {codigo_clase}: {destinatarios}")


def procesar():

    # BLOQUEO PARA EVITAR DUPLICADOS
    if os.path.exists(LOCK_FILE):
        log("🚫 El script ya está ejecutándose. Cancelado.")
        return
    open(LOCK_FILE, "w").close()

    log("▶️ Iniciando comprobación del Padlet expulsiones…")

    profesores = cargar_profesores()
    log(f"✔️ Profesores cargados: {profesores}")

    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            ultima_str = data.get("ultima_fecha")
            if ultima_str:
                ultima_fecha = datetime.fromisoformat(ultima_str)
            else:
                ultima_fecha = datetime.min.replace(tzinfo=timezone.utc)
    else:
        ultima_fecha = datetime.min.replace(tzinfo=timezone.utc)

    log(f"✔️ Última fecha procesada: {ultima_fecha}")

    resp = requests.get(RSS_URL)
    root = ET.fromstring(resp.content)
    items = root.findall("./channel/item")
    log(f"✔️ Entradas RSS detectadas: {len(items)}")

    nueva_fecha_max = ultima_fecha
    cambios = False

    for item in items:
        title = item.findtext("title", default="")
        desc_html = item.findtext("description", default="")
        pub = item.findtext("pubDate", default="")

        try:
            pubDate = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z")
        except:
            pubDate = datetime.min.replace(tzinfo=timezone.utc)

        if pubDate <= ultima_fecha:
            continue

        # Limpia HTML en el contenido
        contenido = re.sub("<.*?>", "", desc_html).strip()

        # Enviar SOLO a los grupos que aparecen
        for codigo_clase, correos in profesores.items():
            if codigo_clase.upper() in contenido.upper():
                enviar_email(correos, codigo_clase, title, contenido)
                cambios = True

        if pubDate > nueva_fecha_max:
            nueva_fecha_max = pubDate

    if cambios:
        with open(ESTADO_FILE, "w", encoding="utf-8") as f:
            json.dump({"ultima_fecha": nueva_fecha_max.isoformat()}, f)
        log("💾 Estado actualizado.")
    else:
        log("ℹ️ No había cambios nuevos.")

    os.remove(LOCK_FILE)
    log("🔚 Script completado sin errores.")


if __name__ == "__main__":
    procesar()











