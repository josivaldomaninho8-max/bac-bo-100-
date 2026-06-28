import os
import time
import logging
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from twilio.rest import Client
from dotenv import load_dotenv
from flask import Flask, request
import threading

# Carregar variáveis de ambiente
load_dotenv()

# --- CONFIGURAÇÕES ---
WHATSAPP_FROM = os.getenv("+14155238886")
WHATSAPP_TO = os.getenv("+244922105228")
TWILIO_SID = os.getenv("ACc6d1f7856b4388d2be984b9976392a9c")
TWILIO_AUTH_TOKEN = os.getenv("7d3e410740ae00fcd23e060e246e8eae")
USERNAME = os.getenv("925959236")
PASSWORD = os.getenv("Senhas.925")

# --- SETUP TWILIO WHATSAPP ---
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

def enviar_whatsapp(mensagem):
    """Envia mensagem via WhatsApp usando Twilio"""
    try:
        message = twilio_client.messages.create(
            from_=f'whatsapp:{WHATSAPP_FROM}',
            body=mensagem,
            to=f'whatsapp:{WHATSAPP_TO}'
        )
        print(f"✅ Mensagem enviada: {mensagem}")
        return message.sid
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        return None

# --- SETUP SELENIUM ---
def iniciar_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- LOGIN NA ELEPHANTEBET ---
def login_elephantebet(driver):
    try:
        driver.get("https://elephantbet.co.ao")
        time.sleep(5)
        
        # Tentar encontrar botão de login
        login_btn = driver.find_element(By.CLASS_NAME, "login")
        login_btn.click()
        time.sleep(2)
        
        # Preencher credenciais
        username_field = driver.find_element(By.NAME, "username")
        username_field.send_keys(USERNAME)
        
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(PASSWORD)
        password_field.send_keys(Keys.ENTER)
        time.sleep(5)
        return True
    except Exception as e:
        print(f"Erro no login: {e}")
        return False

# --- COLETAR RESULTADOS DO BACBO ---
def coletar_resultados(driver):
    try:
        driver.get("https://elephantbet.co.ao/casino")
        time.sleep(10)
        
        resultados = []
        # Aguardar elementos carregarem
        elementos = driver.find_elements(By.CSS_SELECTOR, ".history-result-circle")
        
        for e in elementos[:20]:
            texto = e.text.strip().upper()
            if texto in ["B", "P", "T"]:
                resultados.append(texto)
        
        return resultados
    except Exception as e:
        print(f"Erro ao coletar resultados: {e}")
        return []

# --- ANALISAR TENDÊNCIA ---
def prever_sinal(resultados):
    if not resultados or len(resultados) < 3:
        return "⚠️ Sem dados suficientes"
    
    ultimos = resultados[:5]
    count = {"B": 0, "P": 0, "T": 0}
    
    for r in ultimos:
        if r in count:
            count[r] += 1
    
    # Lógica de previsão
    if count["B"] >= 3:
        return "🔵 AZUL (B) - Alta probabilidade"
    elif count["P"] >= 3:
        return "🔴 VERMELHO (P) - Alta probabilidade"
    elif count["T"] >= 2:
        return "🟡 EMPATE (T) - Médio risco"
    else:
        # Se não houver tendência clara, sugerir o último resultado
        ultimo = ultimos[0] if ultimos else "P"
        if ultimo == "B":
            return "🔵 AZUL (B) - Seguindo tendência"
        elif ultimo == "T":
            return "🟡 EMPATE (T) - Seguindo tendência"
        else:
            return "🔴 VERMELHO (P) - Seguindo tendência"

# --- TAREFA PRINCIPAL ---
def enviar_sinal():
    print("🔄 Iniciando coleta de sinais...")
    driver = None
    try:
        driver = iniciar_driver()
        if login_elephantebet(driver):
            resultados = coletar_resultados(driver)
            sinal = prever_sinal(resultados)
            
            # Formatar mensagem
            mensagem = f"""🎯 *SINAL BAC BO* 🎯

📊 Análise: {sinal}

📈 Últimos resultados: {' → '.join(resultados[:10])}

⏰ {time.strftime('%H:%M:%S')}
🏆 ElephantBet.ao"""
            
            # Enviar via WhatsApp
            enviar_whatsapp(mensagem)
        else:
            enviar_whatsapp("⚠️ Falha no login da ElephantBet. Verificando...")
    except Exception as e:
        print(f"❌ Erro: {e}")
        enviar_whatsapp(f"❌ Erro no bot: {str(e)[:50]}")
    finally:
        if driver:
            driver.quit()

# --- FLASK PARA KEEP-ALIVE (Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Bac Bo está rodando!"

@app.route('/health')
def health():
    return "OK", 200

# --- INICIAR AGENDAMENTO ---
def iniciar_bot():
    # Executar uma vez ao iniciar
    enviar_sinal()
    
    # Agendar a cada 5 minutos (para não sobrecarregar)
    schedule.every(5).minutes.do(enviar_sinal)
    
    print("🚀 Bot de sinais Bac Bo iniciado!")
    print(f"📱 Enviando para: {WHATSAPP_TO}")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- PONTO DE ENTRADA ---
if __name__ == "__main__":
    # Iniciar bot em thread separada
    bot_thread = threading.Thread(target=iniciar_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
