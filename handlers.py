# handlers.py
import logging
import os
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    SUPER_ADMIN_IDS, CRYPTO_CURRENCIES,
    CRYPTO_RATES, MIN_AMOUNT, PAYMENT_DETAILS, RECEIPTS_FOLDER
)
from messages import get_text

logger = logging.getLogger(__name__)


# Состояния FSM
class ExchangeStates(StatesGroup):
    waiting_crypto = State()
    waiting_amount = State()
    waiting_wallet = State()
    confirming = State()
    waiting_receipt = State()


class AdminStates(StatesGroup):
    waiting_referral_name = State()


def register_handlers(dp, db, bot):
    router = Router()
    dp.include_router(router)

    # Вспомогательные функции
    async def safe_edit_message(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode='HTML'):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

    async def process_referral(user_id: int, username: str, start_args: str):
        """Обработка реферальной ссылки"""
        if not start_args:
            return None

        # Проверяем, есть ли уже реферер у пользователя
        current_referrer = db.get_referrer_id(user_id)
        if current_referrer:
            return current_referrer

        # Обеспечиваем существование пользователя
        db.ensure_user_exists(user_id, username)

        referrer_id = None

        # Пробуем найти реферальную ссылку
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM referral_links WHERE referral_code = ?', (start_args,))
        result = cursor.fetchone()
        if result:
            referrer_id = result[0]
        else:
            # Пробуем преобразовать в число (старый формат)
            try:
                referrer_candidate = int(start_args)
                # Проверяем что это не сам пользователь и пользователь существует
                if (user_id != referrer_candidate and
                        referrer_candidate in db.get_all_users() and
                        referrer_candidate in SUPER_ADMIN_IDS):
                    referrer_id = referrer_candidate
            except ValueError:
                pass

        conn.close()

        # Устанавливаем реферера
        if referrer_id and referrer_id != user_id:
            db.set_user_referrer(user_id, referrer_id)
            return referrer_id

        return None

    async def show_main_menu(event, user_id: int = None, username: str = None):
        if isinstance(event, types.Message):
            message = event
            user_id = user_id or message.from_user.id
        elif isinstance(event, types.CallbackQuery):
            message = event.message
            user_id = user_id or event.from_user.id
        else:
            return

        user_role = db.get_user_role(user_id)

        keyboard = InlineKeyboardBuilder()

        if user_role == 'super_admin':
            keyboard.button(text=get_text("exchange_button"), callback_data="exchange")
            keyboard.button(text=get_text("super_admin_button"), callback_data="super_admin")
            welcome_text = get_text("super_admin_welcome")
        else:
            keyboard.button(text=get_text("exchange_button"), callback_data="exchange")
            keyboard.button(text=get_text("support_button"), callback_data="support")
            welcome_text = get_text("user_welcome")

        keyboard.adjust(1)

        base_text = get_text("start_message", welcome_text=welcome_text)

        if isinstance(event, types.Message):
            await message.answer(base_text, reply_markup=keyboard.as_markup(), parse_mode='HTML')
        else:
            await safe_edit_message(
                message.chat.id,
                message.message_id,
                base_text,
                keyboard.as_markup()
            )

    # Команда /start с обработкой реферальных ссылок
    @router.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        # Очищаем состояние при старте
        await state.clear()

        user_id = message.from_user.id
        username = message.from_user.username or ""

        # Обрабатываем реферальную ссылку
        start_args = message.text.split()[1] if len(message.text.split()) > 1 else None
        if start_args:
            referrer_id = await process_referral(user_id, username, start_args)
            if referrer_id:
                logger.info(f"Пользователь {user_id} зарегистрирован по ссылке от {referrer_id}")

        await show_main_menu(message, user_id, username)

    # Админ панель
    async def show_admin_panel(event):
        if isinstance(event, types.Message):
            message = event
        elif isinstance(event, types.CallbackQuery):
            message = event.message

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=get_text("stats_button"), callback_data="admin_stats")
        keyboard.button(text=get_text("referral_links_button"), callback_data="admin_referral_links")
        keyboard.button(text=get_text("create_referral_button"), callback_data="create_referral")
        keyboard.button(text=get_text("main_menu_button"), callback_data="back_to_main")
        keyboard.adjust(1)

        text = get_text("super_admin_panel")

        if isinstance(event, types.Message):
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode='HTML')
        else:
            await safe_edit_message(message.chat.id, message.message_id, text, keyboard.as_markup())

    # Статистика админа
    @router.callback_query(F.data == "admin_stats")
    async def admin_stats(callback: types.CallbackQuery):
        if db.get_user_role(callback.from_user.id) != 'super_admin':
            await callback.answer(get_text("access_denied"), show_alert=True)
            return

        stats = db.get_admin_stats(callback.from_user.id)
        if not stats:
            await callback.answer("❌ Ошибка получения статистики", show_alert=True)
            return

        stats_text = get_text(
            "admin_stats",
            total_orders=stats['total_orders'],
            completed_orders=stats['completed_orders'],
            waiting_orders=stats['waiting_orders'],
            processing_orders=stats['processing_orders'],
            total_amount=stats['total_amount'],
            total_referrals=stats['total_referrals']
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=get_text("back_button"), callback_data="super_admin")
        await safe_edit_message(callback.message.chat.id, callback.message.message_id, stats_text, keyboard.as_markup())

    # Список реферальных ссылок
    @router.callback_query(F.data == "admin_referral_links")
    async def admin_referral_links(callback: types.CallbackQuery):
        if db.get_user_role(callback.from_user.id) != 'super_admin':
            await callback.answer(get_text("access_denied"), show_alert=True)
            return

        links = db.get_referral_links(callback.from_user.id)

        if not links:
            await callback.answer("❌ Нет реферальных ссылок", show_alert=True)
            return

        links_list = ""
        for link in links:
            referral_link = f"https://t.me/{(await bot.get_me()).username}?start={link['code']}"
            links_list += get_text(
                "referral_link_stats",
                name=link['name'],
                referrals_count=link['stats']['referrals_count'],
                orders_count=link['stats']['orders_count'],
                total_amount=link['stats']['total_amount'],
                referral_link=referral_link
            ) + "\n\n"

        text = get_text("referral_links_list", links_list=links_list)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=get_text("back_button"), callback_data="super_admin")
        await safe_edit_message(callback.message.chat.id, callback.message.message_id, text, keyboard.as_markup())

    # Создание реферальной ссылки
    @router.callback_query(F.data == "create_referral")
    async def create_referral(callback: types.CallbackQuery, state: FSMContext):
        if db.get_user_role(callback.from_user.id) != 'super_admin':
            await callback.answer(get_text("access_denied"), show_alert=True)
            return

        await callback.message.answer(get_text("create_referral_prompt"))
        await state.set_state(AdminStates.waiting_referral_name)

    # Обработка названия реферальной ссылки
    @router.message(AdminStates.waiting_referral_name)
    async def process_referral_name(message: types.Message, state: FSMContext):
        if db.get_user_role(message.from_user.id) != 'super_admin':
            await message.answer(get_text("access_denied"))
            return

        name = message.text.strip()
        if not name:
            await message.answer("❌ Название не может быть пустым")
            return

        referral_code = db.create_referral_link(message.from_user.id, name)
        if not referral_code:
            await message.answer("❌ Ошибка создания ссылки")
            return

        referral_link = f"https://t.me/{(await bot.get_me()).username}?start={referral_code}"

        await message.answer(
            get_text("referral_created", name=name, referral_link=referral_link),
            parse_mode='HTML'
        )
        await state.clear()

    # Callback обработчики для админ-панели
    @router.callback_query(F.data == "super_admin")
    async def super_admin_panel(callback: types.CallbackQuery):
        if db.get_user_role(callback.from_user.id) != 'super_admin':
            await callback.answer(get_text("access_denied"), show_alert=True)
            return
        await show_admin_panel(callback)

    # Обмен криптовалютой
    @router.callback_query(F.data == "exchange")
    async def show_crypto_selection(callback: types.CallbackQuery, state: FSMContext):
        # Очищаем состояние при начале нового обмена
        await state.clear()

        user_id = callback.from_user.id
        user_role = db.get_user_role(user_id)

        # Для обычных пользователей не используем реферальные ссылки
        referral_code = None

        await state.update_data(referral_code=referral_code)

        keyboard = InlineKeyboardBuilder()
        for crypto_code, crypto_name in CRYPTO_CURRENCIES.items():
            keyboard.button(text=crypto_name, callback_data=f"crypto_{crypto_code}")
        keyboard.button(text=get_text("back_button"), callback_data="back_to_main")
        keyboard.adjust(1)

        await safe_edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            get_text("select_crypto"),
            keyboard.as_markup()
        )
        await state.set_state(ExchangeStates.waiting_crypto)

    # Выбор криптовалюты
    @router.callback_query(F.data.startswith("crypto_"))
    async def select_crypto(callback: types.CallbackQuery, state: FSMContext):
        crypto_type = callback.data.split("_")[1]
        await state.update_data(crypto_type=crypto_type)

        await safe_edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            get_text("enter_amount",
                     crypto_name=CRYPTO_CURRENCIES[crypto_type],
                     min_amount=MIN_AMOUNT),
            parse_mode='HTML'
        )
        await state.set_state(ExchangeStates.waiting_amount)

    # Ввод суммы
    @router.message(ExchangeStates.waiting_amount)
    async def process_amount(message: types.Message, state: FSMContext):
        try:
            amount = float(message.text.replace(',', '.'))
            if amount < MIN_AMOUNT:
                await message.answer(get_text("min_amount_error", min_amount=MIN_AMOUNT))
                return

            await state.update_data(amount_rub=amount)

            data = await state.get_data()
            crypto_type = data['crypto_type']

            # Расчет криптовалюты
            crypto_amount = amount / CRYPTO_RATES[crypto_type]

            await state.update_data(crypto_amount=round(crypto_amount, 8))

            await message.answer(
                get_text("enter_wallet",
                         amount=amount,
                         crypto_amount=crypto_amount,
                         crypto_type=crypto_type),
                parse_mode='HTML'
            )
            await state.set_state(ExchangeStates.waiting_wallet)

        except ValueError:
            await message.answer(get_text("invalid_amount"))

    # Ввод кошелька
    @router.message(ExchangeStates.waiting_wallet)
    async def process_wallet(message: types.Message, state: FSMContext):
        wallet_address = message.text.strip()
        await state.update_data(wallet_address=wallet_address)

        data = await state.get_data()
        comment = db.generate_comment()

        await state.update_data(comment=comment)

        payment_details = get_text("payment_details",
                                   phone=PAYMENT_DETAILS['phone'],
                                   bank=PAYMENT_DETAILS['bank'],
                                   comment=comment)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=get_text("confirm_button"), callback_data="confirm_order")
        keyboard.button(text=get_text("cancel_button"), callback_data="cancel_order")
        keyboard.adjust(2)

        await message.answer(
            get_text("order_details",
                     amount_rub=data['amount_rub'],
                     crypto_amount=data['crypto_amount'],
                     crypto_type=data['crypto_type'],
                     wallet_address=wallet_address,
                     payment_details=payment_details),
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        await state.set_state(ExchangeStates.confirming)

    # Подтверждение заявки
    @router.callback_query(F.data == "confirm_order")
    async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
        try:
            data = await state.get_data()

            # Проверяем, что все необходимые данные есть
            required_fields = ['amount_rub', 'crypto_type', 'crypto_amount', 'wallet_address', 'comment']
            for field in required_fields:
                if field not in data:
                    await callback.answer(f"❌ Отсутствуют данные: {field}", show_alert=True)
                    return

            # Сохранение заявки в БД
            order_id = db.create_order({
                'user_id': callback.from_user.id,
                'username': callback.from_user.username or "No username",
                'amount_rub': data['amount_rub'],
                'crypto_type': data['crypto_type'],
                'crypto_amount': data['crypto_amount'],
                'wallet_address': data['wallet_address'],
                'comment': data['comment'],
                'referral_code': data.get('referral_code')
            })

            # Сохраняем order_id в состоянии
            await state.update_data(order_id=order_id)

            await callback.message.edit_text(
                "⚠️ <b>Платеж не обнаружен</b>\n\n"
                f"📋 <b>Детали заявки #{order_id}:</b>\n"
                f"💵 Сумма: {data['amount_rub']:,.2f} RUB\n"
                f"💰 Криптовалюта: {data['crypto_amount']:.8f} {data['crypto_type']}\n"
                f"🔐 Комментарий: {data['comment']}\n\n"
                "💳 <b>Реквизиты для оплаты:</b>\n"
                f"📞 СБП: {PAYMENT_DETAILS['phone']}\n"
                f"🏦 Банк: {PAYMENT_DETAILS['bank']}\n\n"
                "🔸 <b>Переведите указанную сумму</b>\n"
                "🔸 <b>Обязательно укажите комментарий к платежу</b>\n"
                "🔸 <b>После оплаты отправьте скриншот чека</b>\n\n"
                "<i>После проверки чека администратором криптовалюта будет отправлена на ваш кошелек</i>",
                parse_mode='HTML'
            )

            # Переходим в состояние ожидания чека
            await state.set_state(ExchangeStates.waiting_receipt)

        except Exception as e:
            logger.error(f"Ошибка при создании заявки: {e}")
            await callback.answer("❌ Ошибка при создании заявки", show_alert=True)

    # Отмена заявки
    @router.callback_query(F.data == "cancel_order")
    async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(get_text("order_cancelled"))
        await show_main_menu(callback)

    # Поддержка
    @router.callback_query(F.data == "support")
    async def show_support(callback: types.CallbackQuery):
        await safe_edit_message(callback.message.chat.id, callback.message.message_id, get_text("support"))

    # Назад в главное меню
    @router.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await show_main_menu(callback)

    # Обработчик для фото (чеков)
    @router.message(F.photo)
    async def handle_receipt_photo(message: types.Message, state: FSMContext):
        """Обработка фотографии чека"""
        user_id = message.from_user.id

        # Сохраняем фото в папку receipts
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Создаем уникальное имя файла
        file_extension = os.path.splitext(file_path)[1]
        filename = f"receipt_{user_id}_{message.message_id}{file_extension}"
        local_path = os.path.join(RECEIPTS_FOLDER, filename)

        # Скачиваем файл
        await bot.download_file(file_path, local_path)

        # Сохраняем путь в БД (если есть активный заказ)
        current_state = await state.get_state()
        if current_state == ExchangeStates.waiting_receipt.state:
            data = await state.get_data()
            order_id = data.get('order_id')
            if order_id:
                db.save_receipt_path(order_id, local_path)
                await message.answer(
                    "✅ <b>Чек сохранен!</b>\n\n"
                    "⏳ <i>Ожидайте проверки администратором. После подтверждения оплаты "
                    "криптовалюта будет отправлена на ваш кошелек.</i>",
                    parse_mode='HTML'
                )
                await state.clear()
            else:
                await message.answer("❌ Не найдена активная заявка")
        else:
            await message.answer("❌ Нет активной заявки для прикрепления чека")

    # Обработчик для документов (чеков в виде файлов)
    @router.message(F.document)
    async def handle_receipt_document(message: types.Message, state: FSMContext):
        """Обработка документа чека"""
        user_id = message.from_user.id

        # Сохраняем документ в папку receipts
        document = message.document
        file_id = document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Создаем уникальное имя файла
        file_extension = os.path.splitext(file_path)[1]
        filename = f"receipt_{user_id}_{message.message_id}{file_extension}"
        local_path = os.path.join(RECEIPTS_FOLDER, filename)

        # Скачиваем файл
        await bot.download_file(file_path, local_path)

        # Сохраняем путь в БД (если есть активный заказ)
        current_state = await state.get_state()
        if current_state == ExchangeStates.waiting_receipt.state:
            data = await state.get_data()
            order_id = data.get('order_id')
            if order_id:
                db.save_receipt_path(order_id, local_path)
                await message.answer(
                    "✅ <b>Чек сохранен!</b>\n\n"
                    "⏳ <i>Ожидайте проверки администратором. После подтверждения оплаты "
                    "криптовалюта будет отправлена на ваш кошелек.</i>",
                    parse_mode='HTML'
                )
                await state.clear()
            else:
                await message.answer("❌ Не найдена активная заявка")
        else:
            await message.answer("❌ Нет активной заявки для прикрепления чека")