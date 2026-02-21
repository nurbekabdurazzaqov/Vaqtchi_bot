import os
import threading
from flask import Flask
from bot import main

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti! 🤖"

@app.route('/health')
def health():
    return "OK"

def run_bot():
    main()

if __name__ == "__main__":
    # Botni alohida threadda ishga tushirish
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Flask serverni ishga tushirish
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
