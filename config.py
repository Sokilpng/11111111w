# config.py
import os
from typing import Dict, Set

# Основные настройки бота
BOT_TOKEN = "8438525933:AAF8Wm4djl2NKgWIThIPuJ-RYMbIAFsbYUA"
SUPER_ADMIN_IDS = {8327116123}

# Настройки путей
DB_PATH = 'exchange_bot.db'
RECEIPTS_FOLDER = "receipts"

# Настройки криптовалют
CRYPTO_CURRENCIES = {
    'BTC': 'BTC (Bitcoin)',
    'ETH': 'ETH (Ethereum)',
    'LTC': 'LTC (Litecoin)',
    'USDT': 'USDT (Tether)'
}

# Курсы обмена
CRYPTO_RATES = {
    'USDT': 90.0,
    'BTC': 3500000.0,
    'ETH': 250000.0,
    'LTC': 8000.0
}

# Лимиты
MIN_AMOUNT = 3000

# Настройки платежей
PAYMENT_DETAILS = {
    'phone': '5354 5102 0453 5214',
    'bank': '-'
}

# Настройки логирования
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'datefmt': '%Y-%m-%d %H:%M:%S'
}