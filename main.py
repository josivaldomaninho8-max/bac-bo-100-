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
from dotenv import load_dotenv
from flask import Flask, request
import threading
import sys

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURAÇÕES COM FALLBACK ---
WHATSAPP_FROM = os.getenv("+14155238886", "")
WHATSAPP_TO = os.getenv("+244922105228", "")
TWILIO_SID = os.getenv("ACc6d1f7856b4388d2be984b9976392a9c", "")
TWILIO_AUTH_TOKEN = os.getenv("7d3e410740ae00fcd23e060e246e8eae", "")
USERNAME = os.getenv("ELEPHANT_USERNAME", "925959236")
PASSWORD = os.getenv("ELEPHANT_PASSWORD", "Senhas.925")

# Verificar se as credenciais existem
if not all([TWILIO_SID, TWILIO_AUTH_TOKEN, WHATSAPP_FROM, WHATSAPP_TO]):
    print("⚠️ AVISO: Variáveis do Twilio não configuradas!")
    print("📝 Configure no Render as variáveis de ambiente:")
    print("   - TWILIO_SID")
    print("   - TWILIO_AUTH_TOKEN")
    print("   - WHATSAPP_FROM (ex: +14155238886)")
    print("   - WHATSAPP_TO (ex: +244900000000)")
    print("\n💡 O bot continuará rodando com logs, mas NÃO enviará WhatsApp.")
    print("   Use o Render Dashboard -> Environment para configurar.\n")
    
    # Criar cliente Twilio dummy para não quebrar
    class DummyTwilioClient:
        def messages(self):
            return self
        def create(self, **kwargs):
            print(f"📱 [SIMULAÇÃO] Mensagem enviada para {kwargs.get('to')}: {kwargs.get('body')}")
            return None
    
    twilio_client = DummyTwilioClient()
else:
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        print("✅ Twilio configurado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao configurar Twilio: {e}")
        # Fallback para modo simulação
        class DummyTwilioClient:
            def messages(self):
                return self
            def create(self, **kwargs):
                print(f"📱 [SIMULAÇÃO] Mensagem enviada para {kwargs.get('to')}: {kwargs.get('body')}")
                return None
        twilio_client = DummyTwilioClient()

def enviar_whatsapp(mensagem):
    """Envia mensagem via WhatsApp usando Twilio (ou simula se não configurado)"""
    try:
        message = twilio_client.messages.create(
            from_=f'whatsapp:{WHATSAPP_FROM}' if WHATSAPP_FROM else None,
            body=mensagem,
            to=f'whatsapp:{WHATSAPP_TO}' if WHATSAPP_TO else None
        )
        print(f"✅ Mensagem enviada: {mensagem[:50]}...")
        return message.sid if message else None
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        print(f"📝 Mensagem que seria enviada: {mensagem[:100]}...")
        return None

# --- SETUP SELENIUM ---
def iniciar_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    try:
        # Tentar usar webdriver_manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        # Fallback para ChromeDriver no PATH
        driver = webdriver.Chrome(options=options)
    
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
        print("✅ Login realizado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro no login: {e}")
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
        
        print(f"📊 Resultados coletados: {resultados[:10]}")
        return resultados
    except Exception as e:
        print(f"❌ Erro ao coletar resultados: {e}")
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
            
            # Enviar via WhatsApp (ou simular)
            enviar_whatsapp(mensagem)
            print(f"📤 Sinal enviado: {sinal}")
        else:
            enviar_whatsapp("⚠️ Falha no login da ElephantBet. Verificando...")
            print("❌ Falha no login")
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        enviar_whatsapp(f"❌ Erro no bot: {str(e)[:50]}")
    finally:
        if driver:
            driver.quit()
            print("🧹 Driver fechado")

# --- FLASK PARA KEEP-ALIVE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Bac Bo está rodando!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/status')
def status():
    return {
        "status": "running",
        "twilio_configured": bool(TWILIO_SID and TWILIO_AUTH_TOKEN),
        "whatsapp_to": WHATSAPP_TO,
        "username": USERNAME
    }

@app.route('/trigger')
def trigger():
    """Endpoint para testar manualmente"""
    enviar_sinal()
    return "Sinal enviado!", 200

# --- INICIAR AGENDAMENTO ---
def iniciar_bot():
    # Executar uma vez ao iniciar
    print("🚀 Executando primeira análise...")
    enviar_sinal()
    
    # Agendar a cada 5 minutos
    schedule.every(5).minutes.do(enviar_sinal)
    
    print("🚀 Bot de sinais Bac Bo iniciado!")
    print(f"📱 Enviando para: {WHATSAPP_TO if WHATSAPP_TO else 'NÃO CONFIGURADO'}")
    print(f"🔑 Twilio: {'✅ Configurado' if TWILIO_SID else '❌ Não configurado'}")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- PONTO DE ENTRADA ---
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    
    # Iniciar bot em thread separada
    bot_thread = threading.Thread(target=iniciar_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor Flask
    print(f"🌐 Iniciando servidor na porta {port}")
    app.run(host='0.0.0.0', port=port)
