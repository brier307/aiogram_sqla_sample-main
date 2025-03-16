from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.requests import get_orders_page_with_total, get_orders_page_with_total_for_user

import logging
from config import ADMIN

admin_main_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Информация об ордерах💸")],
    [KeyboardButton(text="Информация о пользователе👥")],
    [KeyboardButton(text="Рассылка📨")],
    [KeyboardButton(text="Редактировать настройки бота⚙️")]
], resize_keyboard=True)


admin_settings_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Изменить курс обмена💸", callback_data="edit_rate")],
    [InlineKeyboardButton(text="Изменить контакт поддержки🆘", callback_data="edit_support_contact")],
    [InlineKeyboardButton(text="Управление кошельками👛", callback_data="edit_wallets")]
])


networks_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="BEP-20"), KeyboardButton(text="TRC-20")],
    [KeyboardButton(text="ERC-20"), KeyboardButton(text="TON")],
    [KeyboardButton(text="Выйти🚪")]
], resize_keyboard=True)


wallet_action = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить кошелек➕", callback_data="add_wallet")],
    [InlineKeyboardButton(text="Удалить кошелек🗑", callback_data="delete_wallet")]
])

admin_order_actions = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Завершить✅", callback_data="order_finished")],
    [InlineKeyboardButton(text="Отменить ордер❌", callback_data="cancel_order_by_admin")]
])

admin_warning_buttons = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Отменить❌")],
    [KeyboardButton(text="Не отменять🔙")]
], resize_keyboard=True, one_time_keyboard=True)


order_finish_buttons = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Завершить✅")],
    [KeyboardButton(text="Не завершать🔙")]
], resize_keyboard=True, one_time_keyboard=True)


# Клавиатура для выхода в меню
exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Выйти в меню🚪")]],
    resize_keyboard=True, one_time_keyboard=True)


order_info_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Список ордеров🧾", callback_data="order_list")],
    [InlineKeyboardButton(text="Поиск по номеру🔎", callback_data="search_order")]
])


# Билдер для клавиатуры с инфой об ордерах
def format_order_button_text(order) -> str:
    """Форматирует текст для кнопки ордера"""
    return f"ID: {order.id} | {order.currency} | {order.status}"


# В файле admin_keyboards.py
async def admin_build_orders_keyboard(page: int = 1, user_id: int = None) -> InlineKeyboardMarkup | None:
    try:
        # Список администраторов
        ADMINS = [7185429091]

        # Если пользователь — администратор, показываем все ордера
        if user_id in ADMINS:
            result = await get_orders_page_with_total(page)
            logging.info(f"Admin {user_id} fetching all orders for page {page}")
        else:
            result = await get_orders_page_with_total_for_user(user_id, page)
            logging.info(f"User {user_id} fetching own orders for page {page}")

        orders = result["orders"]
        total_pages = result["total_pages"]

        logging.info(f"Building keyboard for user {user_id}: Orders {len(orders)}, Total pages {total_pages}")

        builder = InlineKeyboardBuilder()

        if not orders:
            builder.add(InlineKeyboardButton(
                text="Нет ордеров на этой странице",
                callback_data="current_page"
            ))
            logging.info(f"No orders found for user {user_id}")
        else:
            for order in orders:
                builder.add(InlineKeyboardButton(
                    text=format_order_button_text(order),
                    callback_data=f"admin_order_info_{order.id}"
                ))
            builder.adjust(1)

        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="←", callback_data=f"order_list_{page - 1}"
            ))
        pagination_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}", callback_data="current_page"
        ))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="→", callback_data=f"order_list_{page + 1}"
            ))
        builder.row(*pagination_buttons)

        return builder.as_markup()
    except Exception as e:
        logging.error(f"Error building orders keyboard for user {user_id}: {e}")
        return None
