import os
import json
import logging
import asyncio
import requests
from flask import Flask, request, jsonify
import bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = "8593303902:AAGMhVPyns29hOX3BRtpEj3bQQeUOo1GUwg"
WEBHOOK_PATH = f"/webhook/{TOKEN}"

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Vaqtchi bot ishlayapti!"
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    try:
        update_data = request.get_json()
        if update_data:
            logger.info(f"📩 Update keldi: {update_data.get('update_id')}")
            
            # Yangi event loop yaratish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.process_update(update_data))
            loop.close()
            
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ Webhook xatolik: {e}")
        return "OK", 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Webhook o'rnatish"""
    try:
        webhook_url = f"https://vaqtchi-bot.onrender.com{WEBHOOK_PATH}"
        telegram_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        
        response = requests.post(telegram_url, json={"url": webhook_url})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_webhook', methods=['GET'])
def delete_webhook():
    """Webhook o'chirish"""
    try:
        telegram_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.post(telegram_url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook_info', methods=['GET'])
def webhook_info():
    """Webhook holatini tekshirish"""
    try:
        telegram_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
        response = requests.get(telegram_url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Flask server {port}-portda ishga tushyapti...")
    app.run(host='0.0.0.0', port=port)
