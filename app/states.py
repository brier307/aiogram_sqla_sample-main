from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    phone_number = State()
    nickname = State()
    bank_card = State()


class OrderForm(StatesGroup):
    currency = State()
    value = State()
    network = State()
    confirm_order = State()


class NicknameChange(StatesGroup):  # Класс для изменения никнейма
    waiting_for_new_nickname = State()


class BankCardChange(StatesGroup):  # Класс для изменения карточки
    waiting_for_new_bank_card = State()


class ExchangeRateChange(StatesGroup):
    waiting_for_new_exchange_rate = State()  # Класс для изменения курса обмена


class SupportContactChange(StatesGroup):
    waiting_for_new_support_contact = State()  # Класс для изменения контакта сапорта


class WalletManagement(StatesGroup):
    waiting_for_network = State()
    waiting_for_address = State()
    waiting_for_delete_address = State()


# Отмена ордера пользователем
class OrderCancel(StatesGroup):
    awaiting_confirmation = State()
    order_id = State()
    original_message_id = State()


# Отмена ордера админом
class OrderCancellation(StatesGroup):
    waiting_for_confirmation = State()


# Состояние для подтверждения транзакции
class OrderPaid(StatesGroup):
    waiting_for_screenshot = State()


# Состояние для получения ID ордера
class OrderInfo(StatesGroup):
    waiting_for_order_id = State()


# Состояние для получения ID юзера
class UserInfo(StatesGroup):
    waiting_for_user_id = State()


class AdminOrderInfo(StatesGroup):
    waiting_for_order_id = State()


# Состояние для рассылки
class Mailing(StatesGroup):
    waiting_for_message = State()
    waiting_for_photo = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()
    confirm_mailing = State()
