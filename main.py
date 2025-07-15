import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage

# — Configuración vía Secrets de Replit
URL                 = os.environ.get("BCV_URL",       "https://www.bcv.org.ve/")
EXCEL_PATH          = os.environ.get("EXCEL_PATH",  "data/tasa_bcv.xlsx")
DESTINATARIOS_PATH  = "data/destinatarios.xlsx"

TELEGRAM_TOKEN      = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

SMTP_HOST           = os.environ.get("SMTP_HOST",    "smtp.gmail.com").strip()
SMTP_PORT           = int(os.environ.get("SMTP_PORT", 587))
EMAIL_ORIGEN        = os.environ["EMAIL_ORIGEN"].strip()
EMAIL_PASS          = os.environ["EMAIL_PASS"].strip()

def enviar_telegram(mensaje):
    print("📡 Enviando Telegram...")
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    resp    = requests.post(url, data=payload)
    if resp.status_code == 200:
        print("✅ Telegram enviado.")
    else:
        print(f"❌ Error Telegram: {resp.status_code}")

def obtener_datos_bcv():
    resp = requests.get(URL, timeout=10, verify=False)
    print("⚠️ Conexión SSL no verificada (solo pruebas)")
    resp.raise_for_status()
    soup  = BeautifulSoup(resp.text, "html.parser")
    dolar = soup.select_one("div#dolar div.centrado strong")
    tasa  = float(dolar.text.strip().replace(",", "."))
    span  = soup.select_one("span.date-display-single")
    fecha = span["content"][:10]
    return fecha, tasa

def guardar_en_excel(fecha, tasa):
    consulta = datetime.now().strftime("%Y-%m-%d")
    fila = {"Fecha BCV": fecha, "Tasa": tasa, "Fecha consulta": consulta}
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)

    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH)
        if fecha in df["Fecha BCV"].astype(str).values:
            print(f"⚠️ Ya hay registro para {fecha}.")
            return False
        df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
        df.to_excel(EXCEL_PATH, index=False)
        print(f"✅ Tasa agregada: {fecha}.")
        return True
    else:
        pd.DataFrame([fila]).to_excel(EXCEL_PATH, index=False)
        print(f"🆕 Excel creado con {fecha}.")
        return True

def enviar_email_excel(fecha, tasa):
    print("📧 Enviando correos electrónicos...")
    df = pd.read_excel(DESTINATARIOS_PATH)

    for _, fila in df.iterrows():
        destino  = fila["email destino"]
        nombre   = fila["nombre destinatario"]
        telefono = fila["texto con telefono para comentarios"]

        msg = EmailMessage()
        msg["Subject"] = f"Tasa BCV del {fecha}"
        msg["From"]    = EMAIL_ORIGEN
        msg["To"]      = destino

        cuerpo = f"""\
Apreciad@ {nombre},

Anexo la última tasa de $ descargada del BCV para la fecha {fecha}.

Tasa oficial: Bs {tasa:.4f}

En caso de algún comentario, favor contactarme por {telefono}.

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
            print(f"❌ Error enviando a {destino}: {e}")

def main():
    print(">>> Iniciando agente BCV <<<")
    try:
        fecha, tasa = obtener_datos_bcv()
        if guardar_en_excel(fecha, tasa):
            enviar_telegram(f"Tasa BCV del {fecha}: Bs {tasa}")
            enviar_email_excel(fecha, tasa)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
