import re
import random
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

from aiogram.fsm.context import FSMContext

from app.states import Form, OrderForm, NicknameChange, BankCardChange, OrderCancel, OrderPaid, OrderInfo

from app.database.requests import (set_user, update_user_data, get_user_info, update_nickname, update_bank_card,
                                   create_order, get_rate, get_wallets, get_order_info, get_support_contact,
                                   update_order_status, get_order_status)
from app.user_keyboard import *
from app.admin_keyboards import admin_order_actions
from config import ADMIN
from app.luhn import validate_card

logging.basicConfig(level=logging.INFO)


# from middlewares import BaseMiddleware

user = Router()

# user.message.middleware(BaseMiddleware())


@user.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Получаем необходимые данные из объекта message.from_user
    tg_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Проверяем, есть ли пользователь в БД
    user_exists = await set_user(tg_id, username, full_name)

    if user_exists:
        await message.answer('Добро пожаловать!\n'
                             'Для изменения настроек профиля воспользуйтесь меню⚙️',
                             reply_markup=user_main_keyboard)
    else:
        await message.answer('Пожалуйста, отправьте ваш номер телефона.', reply_markup=phone_button)
        await state.set_state(Form.phone_number)


# Хендлер для получения номера телефона
@user.message(Form.phone_number, F.contact)
async def process_phone_number(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await update_user_data(message.from_user.id, 'phone_number', phone_number)
    await message.answer('Теперь введите ваш никнейм.', reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.nickname)


# Хендлер для получения никнейма
@user.message(Form.nickname)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text
    await update_user_data(message.from_user.id, 'nickname', nickname)
    await message.answer('Теперь введите номер вашей банковской карты.')
    await state.set_state(Form.bank_card)


# Хендлер для получения номера банковской карты
@user.message(Form.bank_card)
async def process_bank_card(message: Message, state: FSMContext):
    bank_card = message.text

    # Проверка на числовой формат и длину номера карты
    if not re.match(r'^\d{16}$', bank_card):
        await message.answer('Пожалуйста, введите корректный номер карты (16 цифр).')
        return

    # Проверяем валидность номера карты по алгоритму Луна
    if not validate_card(bank_card):
        await message.answer('Неверный номер карты. Попробуйте снова.')
        return

    # Сохраняем данные в БД
    await update_user_data(message.from_user.id, 'bank_card', bank_card)
    await message.answer('Спасибо! Вы прошли регистрацию.', reply_markup=user_main_keyboard)
    await state.clear()


# Вывод информации о профиле
@user.message(F.text == 'Информация о профиле⚙️')
async def profile_info(message: Message):
    tg_id = message.from_user.id
    user_info = await get_user_info(tg_id)

    if user_info:
        profile_details = (
            f"🆔ID: {user_info['tg_id']}\n"
            f"📱Номер телефона: {user_info['phone_number']}\n"
            f"👤Никнейм: {user_info['nickname']}\n"
            f"💳Номер карты: {user_info['bank_card']}"
        )
        await message.answer(f"Информация о профиле:\n{profile_details}",
                             reply_markup=user_profile_menu)
    else:
        await message.answer("Профиль не найден.")


@user.callback_query(F.data == "change_nickname")
async def change_nickname(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Отвечаем на callback
    await callback.message.answer("Введите новый никнейм:")
    await state.set_state(NicknameChange.waiting_for_new_nickname)  # Устанавливаем состояние для ввода никнейма


@user.message(NicknameChange.waiting_for_new_nickname)
async def process_nickname(message: Message, state: FSMContext):
    new_nickname = message.text
    tg_id = message.from_user.id

    # Обновляем никнейм в базе данных
    await update_nickname(tg_id, new_nickname)

    await message.answer(f"Никнейм успешно обновлен на: {new_nickname}")

    # Очищаем состояние и возвращаем пользователя в главное меню
    await state.clear()  # Очищаем состояние
    await message.answer("Вы вернулись в главное меню.", reply_markup=user_main_keyboard)


@user.callback_query(F.data == "change_bank_card")
async def change_bank_card(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Отвечаем на callback
    await callback.message.answer("Введите новую банковскую карту:")
    await state.set_state(BankCardChange.waiting_for_new_bank_card)  # Устанавливаем состояние для ввода никнейма


@user.message(BankCardChange.waiting_for_new_bank_card)
async def process_bank_card(message: Message, state: FSMContext):
    new_bank_card = message.text
    tg_id = message.from_user.id

    # Проверка на числовой формат и длину номера карты
    if not re.match(r'^\d{16}$', new_bank_card):
        await message.answer('Пожалуйста, введите корректный номер карты (16 цифр).')
        return

    # Проверяем валидность номера карты по алгоритму Луна
    if not validate_card(new_bank_card):
        await message.answer('Неверный номер карты. Попробуйте снова.')
        return

    # Обновляем банковскую картку в базе данных
    await update_bank_card(tg_id, new_bank_card)

    await message.answer(f"Банковская карта успешно обновлена на: {new_bank_card}")

    # Очищаем состояние и возвращаем пользователя в главное меню
    await state.clear()  # Очищаем состояние
    await message.answer("Вы вернулись в главное меню.", reply_markup=user_main_keyboard)


# Вывод информации о поддержке
@user.message(F.text == 'Поддержка🆘')
async def support_info(message: Message):
    support_contact = await get_support_contact()
    await message.answer(f"В случае возникновения дополнительных вопросов обращайтесь к {support_contact}")


@user.message(F.text == "Продать USDT💵")
async def start_order(message: Message, state: FSMContext):
    await message.answer("Выберите валюту для ввода суммы:", reply_markup=usdtuah_keyboard)
    await state.set_state(OrderForm.currency)
    logging.info(f"User {message.from_user.id} started order creation")


@user.message(F.text == "Отмена❌")
async def cancel_order(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith('OrderForm:'):
        await state.clear()
        await message.answer("Создание ордера отменено.", reply_markup=user_main_keyboard)
        logging.info(f"User {message.from_user.id} cancelled order creation")


@user.message(OrderForm.currency, F.text.in_(["USDT", "UAH"]))
async def process_currency(message: Message, state: FSMContext):
    currency = message.text
    await state.update_data(currency=currency)

    response_text = (
        f"Вы выбрали {currency}. Теперь введите кол-во USDT, которое хотите обменять на UAH:"
        if currency == "USDT"
        else f"Вы выбрали {currency}. Теперь введите кол-во UAH, которое хотите получить за свои USDT:"
    )

    await message.answer(response_text, reply_markup=user_back_button)
    await state.set_state(OrderForm.value)
    logging.info(f"User {message.from_user.id} selected currency: {currency}")


@user.message(OrderForm.value)
async def process_value(message: Message, state: FSMContext):
    try:
        # Проверяем сначала кнопку "Вернуться"
        if message.text == "Вернуться🔙":
            await message.answer("Выберите валюту для ввода суммы:", reply_markup=usdtuah_keyboard)
            await state.set_state(OrderForm.currency)
            return

        value = float(message.text)
        data = await state.get_data()
        currency = data['currency']
        rate = await get_rate()

        if currency == 'USDT':
            usdt_amount = value
            uah_amount = value * rate
        else:  # UAH
            usdt_amount = value / rate
            uah_amount = value

        # Сохраняем обе суммы в state
        await state.update_data(
            value=usdt_amount,  # Всегда сохраняем значение в USDT
            original_value=value,  # Изначально введенное значение
            original_currency=currency,  # Валюта, в которой пользователь вводил сумму
            converted_value=uah_amount if currency == 'USDT' else usdt_amount  # Сконвертированное значение
        )

        await message.answer("Выберите сеть для перевода:", reply_markup=networks_keyboard)
        await state.set_state(OrderForm.network)
        logging.info(f"User {message.from_user.id} entered value: {value} {currency}")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное числовое значение.", reply_markup=user_back_button)
    except Exception as e:
        logging.error(f"Error in process_value: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=user_back_button)


@user.message(OrderForm.network)
async def process_network(message: Message, state: FSMContext):
    if message.text == "Вернуться🔙":
        data = await state.get_data()
        await message.answer(f"Вы выбрали {data['currency']}. Теперь введите сумму:", reply_markup=user_back_button)
        await state.set_state(OrderForm.value)
        return

    network = message.text
    await state.update_data(network=network)
    await show_order_summary(message, state)
    logging.info(f"User {message.from_user.id} selected network: {network}")


@user.message(OrderForm.confirm_order)
async def process_confirmation(message: Message, state: FSMContext):
    if message.text == "Вернуться🔙":
        await message.answer("Выберите сеть для перевода:", reply_markup=networks_keyboard)
        await state.set_state(OrderForm.network)
        return
    elif message.text in ["Подтвердить", "Отменить"]:
        await confirm_order(message, state)


@user.message(OrderForm.confirm_order, F.text.in_(["Подтвердить", "Отменить"]))
async def confirm_order(message: Message, state: FSMContext):
    if message.text == "Подтвердить":
        try:
            data = await state.get_data()
            user_info = await get_user_info(message.from_user.id)
            rate = await get_rate()

            # Создаем заказ в базе данных и получаем его ID
            # Важно: всегда сохраняем значение в USDT
            order_id = await create_order(
                user_id=message.from_user.id,
                currency='USDT',  # Всегда сохраняем как USDT
                value=str(data['value']),  # Значение в USDT
                exchange_rate=rate,
                network=data['network'],
                bank_card=user_info['bank_card'],
                wallet=data['wallet']
            )

            if not order_id:
                raise ValueError("Failed to create order: no order ID returned")

            order_info = await get_order_info(order_id)

            if not order_info:
                raise ValueError(f"Failed to get order info for order ID: {order_id}")

            # Формируем текст уведомления для администраторов с учетом исходной валюты
            original_currency = data.get('original_currency', 'USDT')
            admin_notification = (
                f"🆕 Новый ордер!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username}) ID:{message.from_user.id}\n"
                f"📱 Телефон: {user_info['phone_number']}\n"
                f"💰 Исходная валюта: {original_currency}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
                f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Отправляем уведомление всем администраторам
            for admin_id in ADMIN:
                try:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=admin_notification,
                        reply_markup=admin_order_actions
                    )
                    logging.info(f"Notification sent to admin {admin_id}")
                except Exception as e:
                    logging.error(f"Failed to send notification to admin {admin_id}: {e}")

            # Уведомление для пользователя
            user_notification = (
                f"🔢 ID ордера: {order_info['id']}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH "
                f"(≈ {float(order_info['value']):.2f} {order_info['currency']})\n"
                f"💱Курс обмена: {order_info['exchange_rate']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"💳 Номер карты для получения UAH: {order_info['bank_card']}\n"
                f"👛 Кошелек для перевода USDT: {order_info['wallet']}\n"
                f"⏳ Статус: {order_info['status']}"
            )

            await message.answer(
                f"Ордер успешно создан!\n\n{user_notification}",
                reply_markup=user_order_actions
            )
            logging.info(f"Order {order_id} created for user {message.from_user.id}")

            await message.answer(
                f"Для просмотра информации о своих ордерах воспользуйтесь главным меню",
                reply_markup=user_main_keyboard
            )

        except Exception as e:
            logging.error(f"Error in confirm_order: {e}")
            await message.answer(
                "Произошла ошибка при создании заказа. Пожалуйста, попробуйте еще раз.",
                reply_markup=user_main_keyboard
            )
        finally:
            await state.clear()
    else:
        await message.answer("Заказ отменен.", reply_markup=user_main_keyboard)
        await state.clear()


@user.message(F.text == "Назад")
async def go_back(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == OrderForm.value:
        await start_order(message, state)
    elif current_state == OrderForm.network:
        await state.set_state(OrderForm.currency)
        await message.answer("Выберите валюту для ввода суммы:", reply_markup=usdtuah_keyboard)
    elif current_state == OrderForm.confirm_order:
        await state.set_state(OrderForm.network)
        await message.answer("Выберите сеть для перевода:", reply_markup=networks_keyboard)
    else:
        await message.answer("Нельзя вернуться назад.", reply_markup=user_main_keyboard)
        await state.clear()
    logging.info(f"User {message.from_user.id} went back from state {current_state}")


async def show_order_summary(message: Message, state: FSMContext):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        user_id = message.from_user.id
        user_info = await get_user_info(user_id)

        # Получаем доступный кошелек
        wallets = await get_wallets()
        matching_wallets = [w for w in wallets if w.network == data['network']]
        wallet = random.choice(matching_wallets).address if matching_wallets else None

        if not wallet:
            await message.answer("Нет доступных кошельков для выбранной сети")
            await state.clear()
            return

        # Получаем актуальный курс из БД
        exchange_rate = await get_rate()

        # Сохраняем данные в состояние для последующего создания ордера
        await state.update_data(
            wallet=wallet,
            bank_card=user_info['bank_card']
        )

        # Формируем предварительный просмотр заказа с учетом исходной валюты
        original_currency = data.get('original_currency', 'USDT')

        # Проверяем наличие необходимых данных
        if 'original_value' not in data:
            raise ValueError("Missing original_value in state data")

        # Формируем строку с суммой в зависимости от валюты
        if original_currency == 'USDT':
            uah_amount = float(data['original_value']) * exchange_rate
            usdt_amount = float(data['original_value'])
        else:  # UAH
            uah_amount = float(data['original_value'])
            usdt_amount = float(data['original_value']) / exchange_rate

        order_summary = (
            f"💵 Сумма: {uah_amount:.2f} UAH "
            f"(≈ {usdt_amount:.2f} USDT)\n"
            f"🌐 Сеть для отправки: {data['network']}\n"
            f"💳 Номер карты для получения: {user_info['bank_card']}\n"
        )

        confirm_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Подтвердить")],
                [KeyboardButton(text="Отменить")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"Проверьте правильность данных:\n{order_summary}\nПодтвердить заказ?",
            reply_markup=confirm_keyboard
        )
        await state.set_state(OrderForm.confirm_order)

    except Exception as e:
        logging.error(f"Error in show_order_summary: {e}")
        await message.answer("Произошла ошибка при формировании заказа. Пожалуйста, попробуйте еще раз.")
        await state.clear()


@user.callback_query(F.data == "cancel_order_by_user")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    try:
        message_text = callback.message.text
        order_id = int(message_text.split('ID ордера: ')[1].split('\n')[0])

        # Проверяем, можно ли изменять статус ордера
        if not await can_user_modify_order(order_id):
            await callback.message.answer(
                "Этот ордер уже обработан администратором и не может быть изменен.",
                reply_markup=user_main_keyboard
            )
            return

        # Сохраняем ID ордера и ID сообщения в состоянии
        await state.update_data(
            order_id=order_id,
            original_message_id=callback.message.message_id
        )
        await state.set_state(OrderCancel.awaiting_confirmation)

        await callback.message.answer(
            "Вы уверены, что хотите отменить ордер?",
            reply_markup=user_warning_buttons
        )
    except Exception as e:
        logging.error(f"Ошибка при инициализации отмены ордера: {e}")
        await callback.message.answer("Не удалось найти информацию об ордере.")


@user.message(OrderCancel.awaiting_confirmation, F.text == "Отменить❌")
async def confirm_cancel(message: Message, state: FSMContext):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        order_id = data.get('order_id')
        original_message_id = data.get('original_message_id')

        if not order_id:
            raise ValueError("ID ордера не найден")

        # Обновляем статус ордера в базе данных
        await update_order_status(order_id, "Ордер отменен пользователем")

        # Получаем обновленную информацию об ордере
        order_info = await get_order_info(order_id)

        if order_info:
            # Удаляем сообщение с информацией об ордере
            if original_message_id:
                try:
                    await message.bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=original_message_id
                    )
                except Exception as e:
                    logging.error(f"Не удалось удалить сообщение: {e}")

            # Уведомляем администраторов про изменения
            for admin_id in ADMIN:
                try:
                    await message.bot.send_message(
                        admin_id,
                        f"❌ Ордер ID № {order_info['id']} был отменен пользователем"
                    )
                except Exception as e:
                    logging.error(f"Не удалось уведомить администратора {admin_id} о отмене ордера: {e}")

            await message.answer(
                "Ордер успешно отменен!",
                reply_markup=user_main_keyboard
            )

        else:
            await message.answer(
                "Не удалось найти информацию об ордере.",
                reply_markup=user_main_keyboard
            )

    except Exception as e:
        logging.error(f"Ошибка в confirm_cancel: {e}")
        await message.answer(
            "Произошла ошибка при отмене ордера.",
            reply_markup=user_main_keyboard
        )
    finally:
        # Удаляем сообщение с вопросом о подтверждении отмены
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение с подтверждением: {e}")

        await state.clear()


@user.message(OrderCancel.awaiting_confirmation, F.text == "Не отменять🔙")
async def cancel_cancellation(message: Message, state: FSMContext):
    try:
        # Удаляем сообщение с вопросом о подтверждении отмены
        await message.delete()
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение с подтверждением: {e}")

    await state.clear()
    await message.answer(
        "Ордер не отменен",
        reply_markup=user_main_keyboard
    )


@user.callback_query(F.data == "order_paid")
async def process_order_paid(callback: CallbackQuery, state: FSMContext):
    try:
        message_text = callback.message.text
        order_id = int(message_text.split('ID ордера: ')[1].split('\n')[0])

        # Check if order can be modified
        if not await can_user_modify_order(order_id):
            await callback.message.answer(
                "Этот ордер уже обработан администратором и не может быть изменен.",
                reply_markup=user_main_keyboard
            )
            return

        # Save order ID and message ID in state
        await state.update_data(
            order_id=order_id,
            original_message_id=callback.message.message_id
        )

        cancel_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await callback.message.answer(
            "📸 Пожалуйста, отправьте скриншот подтверждения оплаты:",
            reply_markup=cancel_keyboard
        )
        await state.set_state(OrderPaid.waiting_for_screenshot)

    except Exception as e:
        logging.error(f"Error in process_order_paid: {e}")
        await callback.message.answer(
            "Произошла ошибка при обработке запроса.",
            reply_markup=user_main_keyboard
        )
        await state.clear()


@user.message(OrderPaid.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext):
    try:
        # Get data from state
        data = await state.get_data()
        order_id = data.get('order_id')
        original_message_id = data.get('original_message_id')

        if not order_id:
            raise ValueError("Order ID not found")

        # Get the largest photo size file_id
        file_id = message.photo[-1].file_id

        # Get current UTC time for payment
        payment_time = datetime.utcnow()

        # Update order status, file_id and payment date
        success = await update_order_status(
            order_id=order_id,
            new_status="Оплачено",
            file_id=file_id,
            payment_date=payment_time
        )

        if not success:
            raise Exception("Failed to update order status")

        # Get updated order info
        order_info = await get_order_info(order_id)

        if order_info:
            # Try to delete original order message
            if original_message_id:
                try:
                    await message.bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=original_message_id
                    )
                except Exception as e:
                    logging.error(f"Failed to delete message: {e}")

            # Notify user
            await message.answer(
                "✅ Скриншот успешно получен!\n"
                "⏳ Ожидайте подтверждения от администратора.",
                reply_markup=user_main_keyboard
            )

            # Format payment datetime for display
            payment_time_str = payment_time.strftime("%Y-%m-%d %H:%M:%S")

            # Prepare admin notification text
            admin_notification = (
                f"💳 Получено подтверждение оплаты!\n\n"
                f"📋 Информация о заказе:\n"
                f"🔢 ID ордера: {order_info['id']}\n"
                f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"💰 Валюта: {order_info['currency']}\n"
                f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH\n"
                f"💱 Курс обмена: {order_info['exchange_rate']}\n"
                f"💳 Номер карты: {order_info['bank_card']}\n"
                f"👛 Кошелек для получения: {order_info['wallet']}\n"
                f"🌐 Сеть: {order_info['network']}\n"
                f"⌚ Время оплаты: {payment_time_str}UTC\n"
                f"⏳ Статус: {order_info['status']}"
            )

            # Send notification with screenshot to admins
            for admin_id in ADMIN:
                try:
                    await message.bot.send_photo(
                        chat_id=admin_id,
                        photo=file_id,
                        caption=admin_notification,
                        reply_markup=admin_order_actions
                    )
                except Exception as e:
                    logging.error(f"Failed to send notification to admin {admin_id}: {e}")

        await state.clear()

    except Exception as e:
        logging.error(f"Error in process_payment_screenshot: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке скриншота.",
            reply_markup=user_main_keyboard
        )
        await state.clear()


async def can_user_modify_order(id: int) -> bool:

    status = await get_order_status(id)
    if status in ["Ордер завершен администратором✅", "Ордер отменен администратором❌"]:
        return False
    return True


@user.message(F.text == "Мои ордера🧾")
async def request_order_id(message: Message, state: FSMContext):
    await message.answer(
        "Тут вы можете найти информацию о своих ордерах по ID или просмотреть список:",
        reply_markup=exit_keyboard
    )
    await state.set_state(OrderInfo.waiting_for_order_id)


@user.message(OrderInfo.waiting_for_order_id)
async def exit_from_request_order_id(message: Message, state: FSMContext):
    if message.text == 'Выйти в меню🚪':
        await message.answer(
            "Вы вернулись в главное меню",
            reply_markup=user_main_keyboard
        )
        await state.clear()
        return


@user.message(OrderInfo.waiting_for_order_id)
async def process_order_id(message: Message, state: FSMContext):
    # Проверяем, является ли введенное значение числом
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите корректный ID ордера (только цифры)",
            reply_markup=exit_keyboard
        )
        return

    order_id = int(message.text)
    order_info = await get_order_info(order_id)

    if order_info is None:
        await message.answer(
            "Ордер с таким ID не найден",
            reply_markup=user_main_keyboard
        )
        await state.clear()
        return

    # Проверяем, принадлежит ли ордер текущему пользователю
    if str(message.from_user.id) != str(order_info['user_id']):
        await message.answer(
            "Это не Ваш ордер. Вы можете просматривать информацию только о своих ордерах.",
            reply_markup=user_main_keyboard
        )
        await state.clear()
        return

    # Форматируем сообщение с информацией об ордере
    order_message = (
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
        f"⏳ Статус: {order_info['status']}"
    )

    # Отправляем сообщение с информацией об ордере и кнопками управления
    await message.answer(
        order_message,
        reply_markup=user_order_actions
    )

    # Возвращаем пользователя в главное меню
    await message.answer(
        "Вы вернулись в главное меню",
        reply_markup=user_main_keyboard
    )
    await state.clear()


@user.message(OrderPaid.waiting_for_screenshot, F.photo)
async def handle_payment_screenshot(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        order_id = data.get('order_id')

        # Get the largest photo size file_id
        file_id = message.photo[-1].file_id

        # Update order status and save file_id
        success = await update_order_status(
            order_id=order_id,
            new_status="Ожидает подтверждения⏳",
            file_id=file_id
        )

        if success:
            order_info = await get_order_info(order_id)
            if order_info:
                # Notify admins about payment
                admin_notification = (
                    f"💳 Оплата получена!\n\n"
                    f"📋 Информация о заказе:\n"
                    f"🔢 ID ордера: {order_info['id']}\n"
                    f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
                    f"💰 Валюта: {order_info['currency']}\n"
                    f"💵 Сумма: {float(order_info['value']) * float(order_info['exchange_rate']):.2f} UAH\n"
                    f"💱 Курс обмена: {order_info['exchange_rate']}\n"
                    f"🌐 Сеть: {order_info['network']}\n"
                    f"⏳ Статус: {order_info['status']}"
                )

                # Send notification with screenshot to admins
                for admin_id in ADMIN:
                    try:
                        # First send the screenshot
                        await message.bot.send_photo(
                            chat_id=admin_id,
                            photo=file_id,
                            caption="📸 Скриншот оплаты"
                        )
                        # Then send order information
                        await message.bot.send_message(
                            chat_id=admin_id,
                            text=admin_notification,
                            reply_markup=admin_order_actions
                        )
                    except Exception as e:
                        logging.error(f"Failed to send notification to admin {admin_id}: {e}")

                await message.answer(
                    "✅ Скриншот успешно получен!\n"
                    "⏳ Ожидайте подтверждения от администратора."
                )
                await state.clear()
            else:
                await message.answer("❌ Произошла ошибка при получении информации о заказе.")
        else:
            await message.answer("❌ Произошла ошибка при обновлении статуса заказа.")

    except Exception as e:
        logging.error(f"Error in handle_payment_screenshot: {e}")
        await message.answer("❌ Произошла ошибка при обработке скриншота.")

    await state.clear()


@user.message(OrderPaid.waiting_for_screenshot)
async def invalid_payment_proof(message: Message):
    """Handle invalid payment proof submissions"""
    if message.text == "Отмена":
        await message.answer(
            "Операция отменена.",
            reply_markup=user_main_keyboard
        )
        return

    await message.answer(
        "❌ Пожалуйста, отправьте скриншот оплаты в виде фотографии.\n"
        "📸 Другие форматы не принимаются.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )