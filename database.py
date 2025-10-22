# database.py
import sqlite3
import random
import string
import logging
from config import DB_PATH, SUPER_ADMIN_IDS

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def generate_referral_code(self):
        return 'ref_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))

    def generate_comment(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referrer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                amount_rub REAL,
                crypto_type TEXT,
                crypto_amount REAL,
                wallet_address TEXT,
                comment TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                receipt_photo_id TEXT,
                receipt_file_path TEXT,
                referral_code TEXT
            )
        ''')

        # Проверяем и добавляем отсутствующие колонки
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'receipt_file_path' not in columns:
            cursor.execute('ALTER TABLE orders ADD COLUMN receipt_file_path TEXT')
            logger.info("Добавлена колонка receipt_file_path в таблицу orders")

        if 'receipt_photo_id' not in columns:
            cursor.execute('ALTER TABLE orders ADD COLUMN receipt_photo_id TEXT')
            logger.info("Добавлена колонка receipt_photo_id в таблицу orders")

        # Таблица реферальных ссылок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                referral_code TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем дефолтные реферальные ссылки для супер-админов
        for admin_id in SUPER_ADMIN_IDS:
            cursor.execute('SELECT COUNT(*) FROM referral_links WHERE user_id = ?', (admin_id,))
            if cursor.fetchone()[0] == 0:
                referral_code = self.generate_referral_code()
                cursor.execute(
                    'INSERT INTO referral_links (user_id, name, referral_code) VALUES (?, ?, ?)',
                    (admin_id, 'Основная ссылка', referral_code)
                )
                logger.info(f"Создана реферальная ссылка для админа: ID {admin_id}")

        conn.commit()
        conn.close()

    def get_user_role(self, user_id: int):
        if user_id in SUPER_ADMIN_IDS:
            return 'super_admin'
        return 'user'

    def get_all_users(self):
        """Получение всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users

    def ensure_user_exists(self, user_id: int, username: str = None):
        """Создание пользователя если не существует"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username or '')
            )
            conn.commit()

        conn.close()

    def set_user_referrer(self, user_id: int, referrer_id: int):
        """Установка реферера для пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE users SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL',
            (referrer_id, user_id)
        )
        conn.commit()
        conn.close()

    def get_referrer_id(self, user_id: int):
        """Получение ID реферера пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT referrer_id FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def create_referral_link(self, user_id: int, name: str):
        """Создание новой реферальной ссылки"""
        if user_id not in SUPER_ADMIN_IDS:
            return None

        referral_code = self.generate_referral_code()
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO referral_links (user_id, name, referral_code) VALUES (?, ?, ?)',
            (user_id, name, referral_code)
        )
        conn.commit()
        conn.close()

        return referral_code

    def get_referral_links(self, user_id: int):
        """Получение всех реферальных ссылок админа"""
        if user_id not in SUPER_ADMIN_IDS:
            return []

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, referral_code FROM referral_links WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        links = cursor.fetchall()
        conn.close()

        result = []
        for link_id, name, referral_code in links:
            stats = self.get_referral_stats(referral_code)
            result.append({
                'id': link_id,
                'name': name,
                'code': referral_code,
                'stats': stats
            })

        return result

    def get_referral_stats(self, referral_code: str):
        """Получение статистики по реферальной ссылке"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Находим user_id владельца ссылки
        cursor.execute('SELECT user_id FROM referral_links WHERE referral_code = ?', (referral_code,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return {'referrals_count': 0, 'orders_count': 0, 'total_amount': 0}

        owner_id = result[0]

        # Количество рефералов (пользователей с этим реферером)
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (owner_id,))
        referrals_count = cursor.fetchone()[0]

        # Количество заявок от рефералов
        cursor.execute('''
            SELECT COUNT(*) FROM orders o 
            JOIN users u ON o.user_id = u.user_id 
            WHERE u.referrer_id = ?
        ''', (owner_id,))
        orders_count = cursor.fetchone()[0]

        # Сумма заявок от рефералов
        cursor.execute('''
            SELECT SUM(amount_rub) FROM orders o 
            JOIN users u ON o.user_id = u.user_id 
            WHERE u.referrer_id = ? AND o.status = "completed"
        ''', (owner_id,))
        total_amount = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'referrals_count': referrals_count,
            'orders_count': orders_count,
            'total_amount': total_amount
        }

    def create_order(self, order_data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO orders (user_id, username, amount_rub, crypto_type, crypto_amount, wallet_address, comment, referral_code, receipt_file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data['user_id'],
            order_data['username'],
            order_data['amount_rub'],
            order_data['crypto_type'],
            order_data['crypto_amount'],
            order_data['wallet_address'],
            order_data['comment'],
            order_data.get('referral_code'),
            order_data.get('receipt_file_path')
        ))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def save_receipt_path(self, order_id: int, file_path: str):
        """Сохранение пути к файлу чека"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE orders SET receipt_file_path = ? WHERE id = ?',
            (file_path, order_id)
        )
        conn.commit()
        conn.close()

    def get_admin_stats(self, user_id: int):
        """Получение общей статистики для администратора"""
        if user_id not in SUPER_ADMIN_IDS:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()

        # Общая статистика по заявкам
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"')
        completed_orders = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "waiting_payment"')
        waiting_orders = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "processing"')
        processing_orders = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(amount_rub) FROM orders WHERE status = "completed"')
        total_amount = cursor.fetchone()[0] or 0

        # Общее количество рефералов
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
        total_referrals = cursor.fetchone()[0]

        conn.close()

        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'waiting_orders': waiting_orders,
            'processing_orders': processing_orders,
            'total_amount': total_amount,
            'total_referrals': total_referrals
        }