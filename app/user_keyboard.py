from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


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
    [InlineKeyboardButton(text="Список ордеров🧾", callback_data="order_list")],
    [InlineKeyboardButton(text="Поиск по номеру🔎", callback_data="search_order")]
])