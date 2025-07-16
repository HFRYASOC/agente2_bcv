import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = os.environ.get("BCV_URL", "https://www.bcv.org.ve/")
EXCEL_PATH = os.path.join("data", "tasa_bcv.xlsx")
DESTINATARIOS_PATH = os.path.join("data", "destinatarios.xlsx")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
EMAIL_ORIGEN = os.environ["EMAIL_ORIGEN"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

def enviar_telegram(mensaje):
    print("📡 Enviando Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        print("→ Status:", resp.status_code)
        print("→ Body:", resp.text)
        if resp.ok:
            print("✅ Telegram enviado.")
        else:
            print("❌ Error Telegram")
    except Exception as e:
        print(f"❌ Telegram fallo: {e}")

def obtener_datos_bcv():
    resp = requests.get(URL, timeout=10, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tasa_str = soup.select_one("div#dolar div.centrado strong").text.strip()
    fecha_str = soup.select_one("span.date-display-single")["content"][:10]
    tasa = float(tasa_str.replace(",", "."))
    return fecha_str, tasa

def guardar_en_excel(fecha, tasa):
    consulta = datetime.now().strftime("%Y-%m-%d")
    fila = {"Fecha BCV": fecha, "Tasa": tasa, "Fecha consulta": consulta}
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)

    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH)
        if fecha in df["Fecha BCV"].astype(str).values:
            print(f"⚠️ Ya existe registro para {fecha}.")
            return False
        df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    else:
        df = pd.DataFrame([fila])

    df.to_excel(EXCEL_PATH, index=False)
    print(f"✅ Registro guardado para {fecha}.")
    return True

def enviar_email_excel(fecha, tasa):
    print("📧 Enviando correos...")
    df = pd.read_excel(DESTINATARIOS_PATH)

    for _, fila in df.iterrows():
        destino = fila["email destino"]
        nombre = fila["nombre destinatario"]
        telefono = fila["texto con telefono para comentarios"]

        msg = EmailMessage()
        msg["Subject"] = f"Tasa BCV del {fecha}"
        msg["From"] = EMAIL_ORIGEN
        msg["To"] = destino

        cuerpo = f"""\
Apreciad@ {nombre},

Anexo la tasa oficial de $ publicada por el BCV para la fecha {fecha}.

Tasa oficial: Bs {tasa:.4f}

Cualquier comentario, puedes escribirme al {telefono}.

Saludos cordiales,
Hans
"""
        msg.set_content(cuerpo)

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ORIGEN, EMAIL_PASS)
                server.send_message(msg)
            print(f"✅ Email enviado a {destino}")
        except Exception as e:
            print(f"❌ Error con {destino}: {e}")

def main():
    print(">>> Iniciando agente BCV <<<")
    try:
        fecha, tasa = obtener_datos_bcv()
        nuevo = guardar_en_excel(fecha, tasa)

        mensaje = f"Tasa BCV del {fecha}: Bs {tasa:.4f}"
        if not nuevo:
            mensaje = "🔄 (Ya registrado) " + mensaje
        enviar_telegram(mensaje)

        if nuevo:
            enviar_email_excel(fecha, tasa)
    except Exception as e:
        print(f"❌ Error general: {e}")
        enviar_telegram(f"🚨 Error agente BCV: {e}")

if __name__ == "__main__":
    main()
