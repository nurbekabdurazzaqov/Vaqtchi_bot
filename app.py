import os
import json
import logging
import asyncio
from flask import Flask, request, jsonify
import bot  # bot.py faylimiz

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bot token
TOKEN = "8593303902:AAGMhVPyns29h0X3BRtpF3h0nal1Qllw"

# Webhook yo'li - Telegram POST so'rovlarini shu yerga yuboradi
WEBHOOK_PATH = f"/webhook/{TOKEN}"

@app.route('/')
def home():
    """Asosiy sahifa - bot ishlayotganini tekshirish"""
    return jsonify({
        "status": "running",
        "message": "Vaqtchi bot ishlayapti!",
        "webhook": f"https://vaqtchi-bot.onrender.com{WEBHOOK_PATH}"
    })

@app.route('/health')
def health():
    """Render health check uchun"""
    return jsonify({"status": "ok"})

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Telegram webhook endpoint - bu yerga POST so'rovlar keladi"""
    try:
        # Telegram dan kelgan JSON ni o'qish
        update_data = request.get_json()
        
        if not update_data:
            logger.error("❌ Bo'sh so'rov keldi")
            return "OK", 200
        
        logger.info(f"📩 Webhook update keldi: {update_data.get('update_id')}")
        
        # Asinxron funktsiyani sinxron tarzda ishga tushirish
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.process_update(update_data))
        loop.close()
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook xatolik: {e}")
        return "OK", 200  # Baribir 200 qaytaramiz, Telegram qayta urinmasligi uchun

@app.route('/set_webhook')
def set_webhook():
    """Webhook ni o'rnatish - bir marta ishga tushirish kerak"""
    import requests
    
    # Render URL
    base_url = "https://vaqtchi-bot.onrender.com"
    webhook_url = f"{base_url}{WEBHOOK_PATH}"
    
    # Telegram API ga so'rov yuborish
    telegram_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    params = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True
    }
    
    try:
        response = requests.post(telegram_url, json=params)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Webhook o'rnatildi: {webhook_url}")
            return jsonify({"success": True, "message": "Webhook o'rnatildi", "url": webhook_url})
        else:
            logger.error(f"❌ Webhook o'rnatilmadi: {result}")
            return jsonify({"success": False, "error": result})
            
    except Exception as e:
        logger.error(f"❌ So'rov xatolik: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/get_webhook_info')
def get_webhook_info():
    """Webhook holatini tekshirish"""
    import requests
    
    telegram_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(telegram_url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/delete_webhook')
def delete_webhook():
    """Webhook ni o'chirish"""
    import requests
    
    telegram_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    
    try:
        response = requests.post(telegram_url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Flask server {port}-portda ishga tushyapti...")
    
    # Webhook ni o'rnatish (faqat bir marta kerak)
    # Eslatma: Buni deploy qilgandan keyin bir marta telefon orqali kiritish kerak
    logger.info("📌 Webhook o'rnatish uchun /set_webhook ga so'rov yuboring")
    
    app.run(host='0.0.0.0', port=port)
