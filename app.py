import os
import threading
import time
import logging
from flask import Flask, jsonify

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bot thread status
bot_running = False
bot_thread = None

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bot": "active" if bot_running else "starting",
        "message": "Telegram bot ishlayapti!"
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/status')
def status():
    return jsonify({
        "bot_running": bot_running,
        "thread_alive": bot_thread.is_alive() if bot_thread else False
    })

def run_bot():
    global bot_running
    try:
        logger.info("🔄 Bot thread ishga tushyapti...")
        from bot import main
        bot_running = True
        logger.info("✅ Bot thread ishga tushdi!")
        main()
    except Exception as e:
        bot_running = False
        logger.error(f"❌ Bot thread xatolik: {e}")
        time.sleep(5)  # 5 soniya kutib qayta urinish
        run_bot()

# Botni ishga tushirish
def start_bot():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot start funksiyasi ishladi")

if __name__ == "__main__":
    # Botni ishga tushirish
    start_bot()
    
    # Flask serverni ishga tushirish
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Flask server {port}-portda ishga tushyapti...")
    app.run(host='0.0.0.0', port=port, debug=False)
