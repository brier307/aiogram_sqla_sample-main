from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.requests import get_orders_page_with_total_for_user
import logging


user_main_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Продать USDT💵")],
    [KeyboardButton(text="Информация о профиле⚙️")],
    [KeyboardButton(text="Мои ордера🧾")],
    [KeyboardButton(text="Поддержка🆘")]
], resize_keyboard=True)

phone_button = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Поделиться контактом📱", request_contact=True)]],
            resize_keyboard=True)

user_profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Изменить никнейм👤", callback_data="change_nickname")],
    [InlineKeyboardButton(text="Изменить карту💳", callback_data="change_bank_card")]
])


usdtuah_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="USDT"), KeyboardButton(text="UAH")],
    [KeyboardButton(text="Отмена❌")]
], resize_keyboard=True, one_time_keyboard=True)

networks_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="BEP-20"), KeyboardButton(text="TRC-20")],
    [KeyboardButton(text="ERC-20"), KeyboardButton(text="TON")],
    [KeyboardButton(text="Вернуться🔙")],
    [KeyboardButton(text="Отмена❌")]
], resize_keyboard=True)


user_order_actions = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пометить, как оплачено✅", callback_data="order_paid")],
    [InlineKeyboardButton(text="Отменить ордер❌", callback_data="cancel_order_by_user")]
])


user_back_button = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Вернуться🔙")],
    [KeyboardButton(text="Отмена❌")]
], resize_keyboard=True)


user_conf_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Подтвердить✅", callback_data="order_paid")],
    [InlineKeyboardButton(text="Отменить ордер❌", callback_data="cancel_order")]
])


user_warning_buttons = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Отменить❌")],
    [KeyboardButton(text="Не отменять🔙")]
], resize_keyboard=True, one_time_keyboard=True)


# Клавиатура для выхода в меню
exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Выйти в меню🚪")]],
    resize_keyboard=True, one_time_keyboard=True)


user_order_info_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Список ордеров🧾", callback_data="order_list_user")],
    [InlineKeyboardButton(text="Поиск по номеру🔎", callback_data="search_order_user")]
])


def format_order_button_text(order) -> str:
    """Форматирует текст для кнопки ордера"""
    return f"ID: {order.id} | {order.currency} | {order.status}"


async def build_orders_keyboard(user_id: int, page: int = 1) -> InlineKeyboardMarkup | None:
    try:
        result = await get_orders_page_with_total_for_user(user_id, page)
        orders = result["orders"]
        total_pages = result["total_pages"]

        logging.info(f"Building keyboard for user {user_id}: Orders {len(orders)}, Total pages {total_pages}")

        if not orders:
            logging.info(f"No orders found for user {user_id}")
            return None

        builder = InlineKeyboardBuilder()
        for order in orders:
            button_text = format_order_button_text(order)
            logging.info(f"Adding order {order.id} with text: {button_text}")
            builder.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"order_info_{order.id}"
            ))
        builder.adjust(1)

        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="←",
                callback_data=f"order_list_{page - 1}"
            ))
        pagination_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="current_page"
        ))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="→",
                callback_data=f"order_list_{page + 1}"
            ))
        builder.row(*pagination_buttons)

        return builder.as_markup()
    except Exception as e:
        logging.error(f"Error building orders keyboard for user {user_id}: {e}")
        return None
