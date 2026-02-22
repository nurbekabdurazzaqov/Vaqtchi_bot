import os
import threading
import time
import logging
import traceback
from flask import Flask, jsonify

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

bot_running = False
bot_thread = None
last_error = None

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bot": "active" if bot_running else "stopped",
        "error": last_error,
        "message": "Telegram bot ishlayapti!"
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/status')
def status():
    return jsonify({
        "bot_running": bot_running,
        "thread_alive": bot_thread.is_alive() if bot_thread else False,
        "last_error": last_error
    })

def run_bot():
    global bot_running, last_error
    try:
        logger.info("🔄 Bot thread ishga tushyapti...")
        from bot import main
        
        # Botni ishga tushirish
        logger.info("✅ Bot thread ishga tushdi! main() chaqirilyapti...")
        bot_running = True
        main()
        
    except Exception as e:
        bot_running = False
        last_error = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"❌ Bot thread xatolik: {e}")
        logger.error(f"❌ Traceback: {error_trace}")
        time.sleep(10)
        run_bot()

def start_bot():
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("✅ Bot start funksiyasi ishladi")
    else:
        logger.info("✅ Bot allaqachon ishlayapti")

if __name__ == "__main__":
    # Botni ishga tushirish
    start_bot()
    
    # Flask serverni ishga tushirish
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Flask server {port}-portda ishga tushyapti...")
    app.run(host='0.0.0.0', port=port, debug=False)
