# messages.py

RU_TEXTS = {
    # Главное меню
    "start_message": (
        "🎯 <b>BAD Exchanger</b> - автоматизированный обменник криптовалют\n\n"
        "🔹 Покупка BTC за RUB\n"
        "🔹 Покупка ETH за RUB\n"
        "🔹 Покупка LTC за RUB\n"
        "🔹 Покупка USDT за RUB\n\n"
        "{welcome_text}"
    ),
    "super_admin_welcome": "Вы вошли как <b>Супер-Администратор</b>",
    "user_welcome": "Чтобы совершить покупку криптовалюты, нажмите <b>♻️ Обменять</b>",

    # Админ-панель
    "super_admin_panel": "🛠️ <b>Панель Супер-Администратора</b>\n\nВыберите действие:",

    # Статистика
    "admin_stats": (
        "📊 <b>Общая статистика</b>\n\n"
        "📈 <b>Заявки:</b>\n"
        "• Всего: {total_orders}\n"
        "• Завершено: {completed_orders}\n"
        "• Ожидают оплаты: {waiting_orders}\n"
        "• В обработке: {processing_orders}\n"
        "• Общая сумма: {total_amount:,.2f} RUB\n\n"
        "👥 <b>Рефералы:</b>\n"
        "• Всего рефералов: {total_referrals}"
    ),

    "referral_link_stats": (
        "🔗 <b>{name}</b>\n"
        "📊 Статистика:\n"
        "• Рефералов: {referrals_count}\n"
        "• Заявок: {orders_count}\n"
        "• Сумма: {total_amount:,.2f} RUB\n"
        "💎 Ссылка: <code>{referral_link}</code>"
    ),

    "referral_links_list": "🔗 <b>Ваши реферальные ссылки</b>\n\n{links_list}",

    "create_referral_prompt": "📝 Введите название для новой реферальной ссылки:",

    "referral_created": (
        "✅ <b>Новая реферальная ссылка создана!</b>\n\n"
        "📝 Название: {name}\n"
        "💎 Ссылка: <code>{referral_link}</code>"
    ),

    # Обмен криптовалютой
    "select_crypto": "💰 <b>Выберите криптовалюту:</b>",
    "enter_amount": (
        "💰 <b>Вы выбрали: {crypto_name}</b>\n\n"
        "💵 <b>Введите сумму в RUB:</b>\n"
        "Минимальная сумма: {min_amount:,} RUB"
    ),
    "enter_wallet": (
        "💵 <b>Сумма:</b> {amount:,.2f} RUB\n"
        "💰 <b>Получите:</b> {crypto_amount:.8f} {crypto_type}\n\n"
        "🔑 <b>Введите адрес кошелька для получения {crypto_type}:</b>"
    ),

    # Заявки
    "order_details": (
        "📋 <b>Детали заявки:</b>\n\n"
        "💵 Сумма: {amount_rub:,.2f} RUB\n"
        "💰 Криптовалюта: {crypto_amount:.8f} {crypto_type}\n"
        "🔑 Кошелек: {wallet_address}\n\n"
        "{payment_details}\n\n"
        "После оплаты отправьте скриншот чека"
    ),

    "payment_details": (
        "💳 <b>СБП:</b> {phone}\n"
        "🏦 <b>Банк:</b> {bank}\n"
        "🔐 <b>Комментарий:</b> {comment}\n\n"
        "<i>Обязательно укажите комментарий!</i>"
    ),

    "order_created": (
        "✅ <b>Заявка создана!</b>\n\n"
        "📋 Номер заявки: #{order_id}\n"
        "💵 Сумма: {amount_rub:,.2f} RUB\n"
        "💰 Криптовалюта: {crypto_amount:.8f} {crypto_type}\n\n"
        "📸 Отправьте скриншот чека об оплате\n\n"
        "⏳ После проверки оплаты криптовалюта будет отправлена на указанный кошелек"
    ),

    # Административные сообщения
    "access_denied": "❌ Доступ запрещен",
    "order_cancelled": "❌ Заявка отменена",
    "invalid_amount": "❌ Введите корректную сумму",
    "min_amount_error": "❌ Минимальная сумма: {min_amount:,} RUB",

    # Поддержка
    "support": (
        "📞 <b>Поддержка BAD Exchanger</b>\n\n"
        "По всем вопросам:\n"
        "• Telegram: @support_bad_exchanger\n"
        "• Email: support@badexchanger.ru\n\n"
        "⏰ Работаем 24/7"
    ),

    # Кнопки
    "exchange_button": "♻️ Обменять",
    "super_admin_button": "🛠️ Админка",
    "support_button": "📞 Поддержка",
    "back_button": "🔙 Назад",
    "main_menu_button": "🔙 Главное меню",
    "confirm_button": "✅ Подтвердить",
    "cancel_button": "❌ Отменить",

    # Админ кнопки
    "stats_button": "📊 Общая статистика",
    "referral_links_button": "🔗 Мои ссылки",
    "create_referral_button": "➕ Создать ссылку"
}


def get_text(key: str, **kwargs) -> str:
    """Получить текст по ключу с форматированием"""
    message_template = RU_TEXTS.get(key, '')

    if not message_template:
        return key

    try:
        return message_template.format(**kwargs)
    except KeyError as e:
        print(f"Warning: Missing placeholder {e} in text key '{key}'")
        return message_template
    except Exception as e:
        print(f"Error formatting text for key '{key}': {str(e)}")
        return key