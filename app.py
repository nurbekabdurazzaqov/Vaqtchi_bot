import os
import threading
import time
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti!"

@app.route('/health')
def health():
    return "OK"

def run_bot():
    try:
        logger.info("🔄 Bot thread ishga tushyapti...")
        import bot
        bot.main()
    except Exception as e:
        logger.error(f"❌ Bot xatolik: {e}")
        time.sleep(10)
        run_bot()

if __name__ == "__main__":
    # Botni threadda ishga tushirish
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    logger.info("✅ Bot start funksiyasi ishladi")
    
    # Flask server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
