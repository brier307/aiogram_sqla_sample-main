import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters import Filter, CommandStart, Command
from aiogram.fsm.context import FSMContext


from app.admin_keyboards import (admin_main_keyboard, admin_settings_menu, networks_keyboard, wallet_action,
                                 admin_warning_buttons, order_finish_buttons, exit_keyboard, admin_order_actions,
                                 order_info_menu, build_orders_keyboard)
from app.database.requests import (get_wallets, get_rate, get_support_contact, update_rate,
                                   update_support_contact, add_wallet, delete_wallet,
                                   update_order_status, get_order_info, get_user_info)
from app.states import (ExchangeRateChange, SupportContactChange, WalletManagement, OrderCancellation, OrderInfo,
                        UserInfo, AdminOrderInfo, Mailing)

from app.admin_func.mailing import start_mailing

import logging
logging.basicConfig(level=logging.DEBUG)


admin = Router()


class Admin(Filter):
    def __init__(self):
        self.admins = [7185429091]

    async def __call__(self, message: Message):
        return message.from_user.id in self.admins
    

@admin.message(Admin(), Command('admin'))
async def cmd_start(message: Message):
    await message.answer('Добро пожаловать в бот, администратор!', reply_markup=admin_main_keyboard)


@admin.message(F.text == 'Редактировать настройки бота⚙️')
async def bot_settings_info(message: Message):
    # Получаем данные из БД
    wallets = await get_wallets()
    rate_value = await get_rate()
    support_contact = await get_support_contact()

    # Форматируем информацию
    wallet_info = "\n".join([f"Сеть: {wallet.network}, Кошелек: {wallet.address}" for wallet in wallets])

    info_message = (
        f"📊 Текущий курс: {rate_value}\n\n"
        f"📞 Контакт поддержки: {support_contact}\n\n"
        f"💼 Кошельки: {wallet_info}"
    )

    # Отправляем одним сообщением
    await message.answer(info_message, reply_markup=admin_settings_menu)


# Меняем курс обмена
@admin.callback_query(F.data == "edit_rate")
async def rate_exchange_change(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Отвечаем на callback
    await callback.message.answer("Отправте новый курс обмена в формате 41.72 (через точку)")
    await state.set_state(ExchangeRateChange.waiting_for_new_exchange_rate)  # Устанавливаем состояние для ввода курса


@admin.message(ExchangeRateChange.waiting_for_new_exchange_rate)
async def process_rate_change(message: Message, state: FSMContext):
    new_exchange_rate = message.text

    # Проверка на значения с плавающей точкой
    if not re.match(r"^-?\d*\.?\d+$", new_exchange_rate):
        await message.answer('Пожалуйста, введите корректный курс\n Через точку, в формате  41.72, 42.0 и т.д.')
        return

    new_exchange_rate = float(new_exchange_rate)

    # Обновляем курс в базе данных
    await update_rate(new_exchange_rate)

    await message.answer(f"Курс успешно обновлен на: {new_exchange_rate}")

    # Очищаем состояние и возвращаем пользователя в главное меню
    await state.clear()  # Очищаем состояние
    await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_keyboard)


# Хендлер на изменение контакта сапорта
@admin.callback_query(F.data == "edit_support_contact")
async def support_contact_change(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Отвечаем на callback
    await callback.message.answer("Отправьте новый контакт тех. поддержки")
    # Устанавливаем состояние для ввода ссылки сапорта
    await state.set_state(SupportContactChange.waiting_for_new_support_contact)


@admin.message(SupportContactChange.waiting_for_new_support_contact)
async def process_contact_change(message: Message, state: FSMContext):
    new_support_contact = message.text

    # Проверка на числовой формат и длину номера карты
    if not re.match(r"^@", new_support_contact):
        await message.answer('Пожалуйста, введите корректный тег пользователя который начинается с @')
        return

    # Обновляем контакт в базе данных
    await update_support_contact(new_support_contact)

    await message.answer(f"Контакт успешно обновлен на: {new_support_contact}")

    # Очищаем состояние и возвращаем пользователя в главное меню
    await state.clear()  # Очищаем состояние
    await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_keyboard)


@admin.callback_query(F.data == "edit_wallets")
async def edit_wallets(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Выберите нужное действие", reply_markup=wallet_action)


# Хендлер для обработки колбэка редактирования кошельков
@admin.callback_query(F.data == "add_wallet")
async def add_wallets(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите сеть (например, BEP-20, TRC-20, ERC-20, TON):",
        reply_markup=networks_keyboard
    )
    await state.set_state(WalletManagement.waiting_for_network)


# Хендлер для состояния ожидания сети
@admin.message(WalletManagement.waiting_for_network)
async def process_network(message: Message, state: FSMContext):
    network = message.text
    await state.update_data(network=network)
    await message.answer("Отправьте адрес криптокошелька:")
    await state.set_state(WalletManagement.waiting_for_address)


# Хендлер для состояния ожидания адреса
@admin.message(WalletManagement.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    address = message.text
    data = await state.get_data()
    network = data.get("network")

    try:
        # Добавляем новый кошелек в базу данных
        await add_wallet(network, address)
        await message.answer(f"Кошелек успешно добавлен:\nСеть: {network}\nАдрес: {address}")

    except Exception as e:
        logging.error(f"Error adding wallet: {e}")
        await message.answer("Произошла ошибка при добавлении кошелька.")

    finally:
        # Очищаем состояние и возвращаемся в главное меню
        await state.clear()
        await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_keyboard)


# Хендлер для обработки колбэка удаления кошельков
@admin.callback_query(F.data == "delete_wallet")
async def delete_wallets(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите адрес криптокошелька, который вы хотите удалить:")
    await state.set_state(WalletManagement.waiting_for_delete_address)


# Хендлер для состояния ожидания адреса
@admin.message(WalletManagement.waiting_for_delete_address)  # Changed from waiting_for_address
async def process_delete_address(message: Message, state: FSMContext):
    address = message.text

    try:
        # Удаляем кошелек из базы данных
        result = await delete_wallet(address)  # Added await here

        if result:
            await message.answer(f"Кошелек с адресом {address} успешно удален.")
        else:
            await message.answer(f"Кошелек с адресом {address} не найден.")

    except Exception as e:
        logging.error(f"Error deleting wallet: {e}")
        await message.answer("Произошла ошибка при удалении кошелька.")

    finally:
        # Очищаем состояние и возвращаемся в главное меню
        await state.clear()
        await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_keyboard)


@admin.callback_query(F.data == "order_finished")
async def finish_order(callback: CallbackQuery):
    try:
        # Get order ID from caption instead of text
        message_caption = callback.message.caption
        if not message_caption:
            raise ValueError("Message caption is empty")

        order_id = int(message_caption.split('ID ордера: ')[1].split('\n')[0])

        # Update order status in database
        await update_order_status(order_id, "Ордер завершен администратором✅")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Format updated message
            updated_caption = (
                f"🔄 Обновление статуса ордера!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
                f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Edit original message (photo with caption)
            await callback.message.edit_caption(
                caption=updated_caption,
                reply_markup=admin_order_actions
            )

            # Notify user about order completion
            try:
                await callback.bot.send_message(
                    order_info['user_id'],
                    f"✅ Ваш ордер #{order_info['id']} был успешно завершен администратором!"
                )
            except Exception as e:
                logging.error(f"Failed to notify user about order completion: {e}")

        await callback.answer("Ордер успешно завершен!")

    except Exception as e:
        logging.error(f"Error in finish_order: {e}")
        await callback.answer("Произошла ошибка при обработке ордера")


@admin.callback_query(F.data == "cancel_order_by_admin")
async def cancel_order_warning(callback: CallbackQuery, state: FSMContext):
    try:
        # Extract order ID from caption instead of text
        message_caption = callback.message.caption
        if not message_caption:
            raise ValueError("Message caption is empty")

        order_id = int(message_caption.split('ID ордера: ')[1].split('\n')[0])

        # Store order ID and message info in state
        await state.update_data({
            'order_id': order_id,
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        })

        # Send warning message with confirmation buttons
        await callback.message.answer(
            "⚠️ Вы уверены, что хотите отменить этот ордер?",
            reply_markup=admin_warning_buttons
        )

        # Set state to waiting for confirmation
        await state.set_state(OrderCancellation.waiting_for_confirmation)

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in cancel_order_warning: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")


@admin.message(OrderCancellation.waiting_for_confirmation, F.text == "Отменить❌")
async def confirm_cancel_order(message: Message, state: FSMContext):
    try:
        # Get order ID and message info from state
        data = await state.get_data()
        order_id = data.get('order_id')
        original_message_id = data.get('message_id')
        chat_id = data.get('chat_id')

        # Update order status in database
        await update_order_status(order_id, "Ордер отменен администратором❌")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Format updated message
            updated_message = (
                f"🔄 Обновление статуса ордера!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
                f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Try to delete the original message
            try:
                await message.bot.delete_message(chat_id=chat_id, message_id=original_message_id)
            except Exception as e:
                logging.error(f"Error deleting original message: {e}")

            # Send new message with updated info
            if order_info.get('file_id'):
                # If there's a screenshot, send photo with caption
                await message.bot.send_photo(
                    chat_id=chat_id,
                    photo=order_info['file_id'],
                    caption=updated_message
                )
            else:
                # If no screenshot, send text message
                await message.bot.send_message(
                    chat_id=chat_id,
                    text=updated_message
                )

            # Notify the user about order cancellation
            try:
                await message.bot.send_message(
                    order_info['user_id'],
                    f"❌ Ваш ордер #{order_info['id']} был отменен администратором"
                )
            except Exception as e:
                logging.error(f"Failed to notify user about order cancellation: {e}")

        await message.answer("Ордер успешно отменен!", reply_markup=admin_main_keyboard)
        await state.clear()

    except Exception as e:
        logging.error(f"Error in confirm_cancel_order: {e}")
        await message.answer("Произошла ошибка при отмене ордера", reply_markup=admin_main_keyboard)
        await state.clear()


@admin.callback_query(F.data == "cancel_order_by_admin")
async def cancel_order_warning(callback: CallbackQuery, state: FSMContext):
    try:
        # Extract order ID and store the message ID for later update
        message_text = callback.message.text
        order_id = int(message_text.split('ID ордера: ')[1].split('\n')[0])

        # Store order ID and message info in state
        await state.update_data({
            'order_id': order_id,
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        })

        # Send warning message with confirmation buttons
        await callback.message.answer(
            "⚠️ Вы уверены, что хотите отменить этот ордер?",
            reply_markup=admin_warning_buttons
        )

        # Set state to waiting for confirmation
        await state.set_state(OrderCancellation.waiting_for_confirmation)

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in cancel_order_warning: {e}")
        await callback.answer("Произошла ошибка при подготовке отмены ордера")


@admin.message(OrderCancellation.waiting_for_confirmation, F.text == "Отменить❌")
async def confirm_cancel_order(message: Message, state: FSMContext):
    try:
        # Get order ID and message info from state
        data = await state.get_data()
        order_id = data.get('order_id')
        original_message_id = data.get('message_id')
        chat_id = data.get('chat_id')

        # Update order status in database
        await update_order_status(order_id, "Ордер отменен администратором")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Format updated message
            updated_message = (
                f"🔄 Обновление статуса ордера!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {order_info['value']} {order_info['currency']} "
                f"(≈ {float(order_info['value']):.2f} {'UAH' if order_info['currency'] == 'USDT' else 'USDT'})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Update the original message without inline keyboard
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=original_message_id,
                text=updated_message
            )

            # Notify the user about order cancellation
            try:
                await message.bot.send_message(
                    order_info['user_id'],
                    f"❌ Ваш ордер #{order_info['id']} был отменен администратором"
                )
            except Exception as e:
                logging.error(f"Failed to notify user about order cancellation: {e}")

        await message.answer("Ордер успешно отменен!", reply_markup=admin_main_keyboard)
        await state.clear()

    except Exception as e:
        logging.error(f"Error in confirm_cancel_order: {e}")
        await message.answer("Произошла ошибка при отмене ордера", reply_markup=admin_main_keyboard)
        await state.clear()


@admin.message(OrderCancellation.waiting_for_confirmation, F.text == "Завершить✅")
async def confirm_finish_order(message: Message, state: FSMContext):
    try:
        # Get order ID and message info from state
        data = await state.get_data()
        order_id = data.get('order_id')
        original_message_id = data.get('message_id')
        chat_id = data.get('chat_id')

        # Update order status in database
        await update_order_status(order_id, "Ордер завершен администратором✅")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Format updated message
            updated_message = (
                f"🔄 Обновление статуса ордера!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {order_info['value']} {order_info['currency']} "
                f"(≈ {float(order_info['value']):.2f} {'UAH' if order_info['currency'] == 'USDT' else 'USDT'})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Update the original message without inline keyboard
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=original_message_id,
                text=updated_message
            )

            # Notify the user about order cancellation
            try:
                await message.bot.send_message(
                    order_info['user_id'],
                    f"✅ Ваш ордер № {order_info['id']} был завершен администратором"
                )
            except Exception as e:
                logging.error(f"Failed to notify user about order finishing: {e}")

        await message.answer("Ордер успешно завершен!", reply_markup=admin_main_keyboard)
        await state.clear()

    except Exception as e:
        logging.error(f"Error in confirm_finish_order: {e}")
        await message.answer("Произошла ошибка при завершении ордера", reply_markup=admin_main_keyboard)
        await state.clear()


@admin.message(OrderCancellation.waiting_for_confirmation, F.text == "Не отменять🔙")
async def cancel_order_cancellation(message: Message, state: FSMContext):
    await message.answer("Действие отменено", reply_markup=admin_main_keyboard)
    await state.clear()


@admin.message(F.text == "Информация об ордерах💸")
async def admin_order_menu(message: Message):
    await message.answer("Тут вы можете искать ордер по ID или просмотреть списком",
                         reply_markup=order_info_menu
                         )


@admin.callback_query(F.data == "search_order")
async def search_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите ID ордера для поиска:",
        reply_markup=exit_keyboard
    )
    await state.set_state(AdminOrderInfo.waiting_for_order_id)
    await callback.answer()


@admin.message(AdminOrderInfo.waiting_for_order_id)
async def process_admin_order_id(message: Message, state: FSMContext):
    if message.text == "Выйти в меню🚪":
        await message.answer("Вы вернулись в главное меню", reply_markup=admin_main_keyboard)
        await state.clear()
        return

    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный ID ордера (только цифры)", reply_markup=exit_keyboard)
        return

    order_id = int(message.text)
    order_info = await get_order_info(order_id)

    if order_info is None:
        await message.answer("Ордер с таким ID не найден", reply_markup=admin_main_keyboard)
        await state.clear()
        return

    order_message = (
        f"📋 Информация об ордере:\n"
        f"🔢 ID: {order_info['id']}\n"
        f"👤 Пользователь: {order_info['user_id']}\n"
        f"💰 Исходная валюта: {order_info['currency']}\n"
        f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
        f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
        f"💱Курс обмена: {order_info['exchange_rate']}\n"
        f"🌐 Сеть: {order_info['network']}\n"
        f"💳 Номер карты: {order_info['bank_card']}\n"
        f"👛 Кошелек для получения: {order_info['wallet']}\n"
        f"⏳ Статус: {order_info['status']}\n"
        f"📅 Создан: {order_info['date_created'].strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await message.answer(order_message, reply_markup=admin_order_actions)
    await message.answer("Ордер найден.\nВыберите действие или воспользуйтесь меню.", reply_markup=admin_main_keyboard)
    await state.clear()


@admin.message(F.text == "Информация о пользователе👥")
async def request_user_id(message: Message, state: FSMContext):
    await message.answer(
        "Введите ID пользователя:",
        reply_markup=exit_keyboard
    )
    await state.set_state(UserInfo.waiting_for_user_id)


@admin.message(UserInfo.waiting_for_user_id)
async def admin_process_user_id(message: Message, state: FSMContext):
    # Проверяем, если админ нажал "Выйти в меню"
    if message.text == "Выйти в меню🚪":
        await message.answer("Вы вернулись в главное меню", reply_markup=admin_main_keyboard)
        await state.clear()
        return
    # Проверяем, является ли введенное значение числом
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите корректный ID пользователя (только цифры)",
            reply_markup=exit_keyboard
        )
        return

    user_id = int(message.text)
    user_info = await get_user_info(user_id)

    if user_info is None:
        await message.answer(
            "Пользователь с таким ID не найден",
            reply_markup=admin_main_keyboard
        )
        await state.clear()
        return

    # Форматируем сообщение с информацией об юзере
    user_info_message = (
        f"👁‍🗨Юзернейм ТГ: {user_info['username']}\n"
        f"🧔‍♂️Имя пользователя: {user_info['full_name']}\n"
        f"📱Номер телефона: {user_info['phone_number']}\n"
        f"👤Никнейм: {user_info['nickname']}\n"
        f"💳Номер карты: {user_info['bank_card']}"
    )

    # Отправляем сообщение с информацией об юзере и кнопками управления
    await message.answer(
        user_info_message,
    )

    # Возвращаем админа в главное меню
    await message.answer(
        "Вы вернулись в главное меню",
        reply_markup=admin_main_keyboard
    )
    await state.clear()


@admin.message(OrderInfo.waiting_for_order_id, F.text == "Выйти в меню🚪")
async def exit_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вы вернулись в главное меню",
        reply_markup=admin_main_keyboard
    )


@admin.callback_query(F.data == "order_list")
@admin.callback_query(F.data.startswith("order_list_"))
async def order_list_handler(callback: CallbackQuery):
    """Обработчик списка ордеров и пагинации"""
    try:
        # Извлекаем номер страницы из callback_data
        command = callback.data
        page = 1 if command == "order_list" else int(command.split("_")[-1])

        # Создаем клавиатуру
        keyboard = await build_orders_keyboard(page)
        if not keyboard:
            await callback.answer("Нет доступных ордеров")
            return

        # Проверяем тип текущего сообщения
        if callback.message.photo:
            # Если текущее сообщение содержит фото, удаляем его и отправляем новое
            await callback.message.delete()
            await callback.message.answer(
                text="Список ордеров:",
                reply_markup=keyboard
            )
        else:
            # Если текущее сообщение текстовое, редактируем его
            await callback.message.edit_text(
                text="Список ордеров:",
                reply_markup=keyboard
            )

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in order list callback: {e}")
        await callback.answer("Произошла ошибка при загрузке списка ордеров")


@admin.callback_query(F.data.startswith("order_info_"))
async def order_info_handler(callback: CallbackQuery):
    """Обработчик просмотра информации об ордере"""
    try:
        # Получаем ID ордера из callback_data
        order_id = int(callback.data.split('_')[-1])

        # Получаем информацию об ордере
        order_info = await get_order_info(order_id)

        if not order_info:
            await callback.answer("Ордер не найден")
            return

        # Форматируем информацию об ордере
        message_text = (
            f"📋 Информация о заказе:\n"
            f"🔢 ID ордера: {order_info['id']}\n"
            f"👤 Пользователь: {order_info['user_id']}\n"
            f"💰 Исходная валюта: {order_info['currency']}\n"
            f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
            f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
            f"💱Курс обмена: {order_info['exchange_rate']}\n"
            f"🌐 Сеть: {order_info['network']}\n"
            f"💳 Номер карты: {order_info['bank_card']}\n"
            f"👛 Кошелек для получения: {order_info['wallet']}\n"
            f"⏳ Статус: {order_info['status']}\n"
            f"📅 Создан: {order_info['date_created'].strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Создаем клавиатуру с кнопками действий
        builder = InlineKeyboardBuilder()

        # Добавляем кнопки действий
        builder.row(InlineKeyboardButton(
            text="Завершить✅",
            callback_data=f"order_finished_{order_id}"
        ))

        builder.row(InlineKeyboardButton(
            text="Отменить ордер❌",
            callback_data=f"cancel_order_by_admin_{order_id}"
        ))

        # Добавляем кнопку "Назад" в последний ряд
        builder.row(InlineKeyboardButton(
            text="« Назад к списку",
            callback_data="order_list"
        ))

        # Если есть file_id (скриншот оплаты), отправляем фото с информацией
        if order_info.get('file_id'):
            try:
                await callback.message.delete()  # Удаляем предыдущее сообщение со списком
                await callback.message.answer_photo(
                    photo=order_info['file_id'],
                    caption=message_text,
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logging.error(f"Error sending photo: {e}")
                # Если не удалось отправить фото, отправляем только текст
                await callback.message.edit_text(
                    text=message_text + "\n\n⚠️ Ошибка загрузки скриншота",
                    reply_markup=builder.as_markup()
                )
        else:
            # Если скриншота нет, отправляем только текст
            await callback.message.edit_text(
                text=message_text + "\n\n📸 Скриншот оплаты отсутствует",
                reply_markup=builder.as_markup()
            )

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in order info callback: {e}")
        await callback.answer("Произошла ошибка при загрузке информации об ордере")


@admin.callback_query(F.data == "current_page")
async def current_page_handler(callback: CallbackQuery):
    """Обработчик нажатия на кнопку текущей страницы"""
    await callback.answer("Текущая страница")


@admin.callback_query(F.data.startswith("cancel_order_by_admin_"))
async def cancel_order_warning_new(callback: CallbackQuery, state: FSMContext):
    try:
        # Извлекаем ID ордера из callback_data
        order_id = int(callback.data.split('_')[-1])

        # Store order ID and message info in state
        await state.update_data({
            'order_id': order_id,
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        })

        # Send warning message with confirmation buttons
        await callback.message.answer(
            "⚠️ Вы уверены, что хотите отменить этот ордер?",
            reply_markup=admin_warning_buttons
        )

        # Set state to waiting for confirmation
        await state.set_state(OrderCancellation.waiting_for_confirmation)

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in cancel_order_warning_new: {e}")
        await callback.answer("Произошла ошибка при подготовке отмены ордера")


@admin.callback_query(F.data.startswith("order_finished_"))
async def finish_order_new(callback: CallbackQuery):
    try:
        # Извлекаем ID ордера из callback_data
        order_id = int(callback.data.split('_')[-1])

        # Update order status in database
        await update_order_status(order_id, "Ордер завершен администратором✅")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Format updated message
            updated_message = (
                f"🔄 Обновление статуса ордера!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
                f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Создаем клавиатуру только с кнопкой "Назад к списку"
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text="« Назад к списку",
                callback_data="order_list"
            ))

            # Delete original message and send new one
            await callback.message.delete()

            if order_info.get('file_id'):
                # If there's a screenshot, send photo with caption
                await callback.message.answer_photo(
                    photo=order_info['file_id'],
                    caption=updated_message,
                    reply_markup=builder.as_markup()
                )
            else:
                # If no screenshot, send text message
                await callback.message.answer(
                    text=updated_message,
                    reply_markup=builder.as_markup()
                )

            # Notify user about order completion
            try:
                await callback.bot.send_message(
                    order_info['user_id'],
                    f"✅ Ваш ордер #{order_info['id']} был успешно завершен администратором!"
                )
            except Exception as e:
                logging.error(f"Failed to notify user about order completion: {e}")

        await callback.answer("Ордер успешно завершен!")

    except Exception as e:
        logging.error(f"Error in finish_order_new: {e}")
        await callback.answer("Произошла ошибка при обработке ордера")


@admin.message(Admin(), F.text == "Рассылка📨")
async def handle_mailing(message: Message, state: FSMContext):
    await start_mailing(message, state)
