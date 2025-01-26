from aiogram import Router, F
from aiogram.types import (Message, InputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
                           InlineKeyboardButton, CallbackQuery)
from aiogram.fsm.context import FSMContext
from app.states import Mailing
from app.database.requests import get_all_users
from app.admin_keyboards import admin_main_keyboard

import logging

mailing = Router()


async def save_current_state(state: FSMContext):
    data = await state.get_data()
    current_state = await state.get_state()
    data['previous_state'] = current_state
    await state.update_data(data)


back_exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Пропустить")],
              [KeyboardButton(text="Назад🔙"), KeyboardButton(text="Выйти🚪")]
              ],
    resize_keyboard=True,
    one_time_keyboard=True
)


@mailing.message(F.text == "Выйти🚪")
async def exit_mailing(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=admin_main_keyboard)


async def start_mailing(message: Message, state: FSMContext):
    await message.answer("Отправьте сообщение для рассылки или нажмите 'Пропустить'.", reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_message)


@mailing.message(Mailing.waiting_for_message, F.text == "Пропустить")
async def skip_message(message: Message, state: FSMContext):
    await state.update_data(message_text="")
    await message.answer("Теперь отправьте фото для рассылки или напишите 'Пропустить'.",
                         reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_photo)


@mailing.message(Mailing.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    await message.answer("Теперь отправьте фото для рассылки или напишите 'Пропустить'.",
                         reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_photo)


@mailing.message(Mailing.waiting_for_photo, F.text == "Пропустить")
async def skip_photo(message: Message, state: FSMContext):
    await state.update_data(photo=None)
    await message.answer("Теперь отправьте текст для кнопки или напишите 'Пропустить'.",
                         reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_button_text)


@mailing.message(Mailing.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)
    await message.answer("Теперь отправьте текст для кнопки или напишите 'Пропустить'.",
                         reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_button_text)


@mailing.message(Mailing.waiting_for_button_text, F.text == "Пропустить")
async def skip_button_text(message: Message, state: FSMContext):
    await state.update_data(buttons=[])
    await show_preview(message, state)


@mailing.message(Mailing.waiting_for_button_text)
async def process_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer("Теперь отправьте URL для кнопки.", reply_markup=back_exit_keyboard)
    await state.set_state(Mailing.waiting_for_button_url)


@mailing.message(Mailing.waiting_for_button_url)
async def process_button_url(message: Message, state: FSMContext):
    data = await state.get_data()
    buttons = [{"text": data["button_text"], "url": message.text}]
    await state.update_data(buttons=buttons)
    await message.answer("Кнопка добавлена.")
    await show_preview(message, state)


async def show_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("message_text", "")
    photo = data.get("photo")
    buttons = data.get("buttons", [])

    if not text and not photo:
        await message.answer("Ошибка: рассылка должна содержать хотя бы текст или фото.",
                           reply_markup=admin_main_keyboard)
        await state.clear()
        return

    if buttons:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button["text"], url=button["url"]) for button in buttons]
        ])
    else:
        markup = None

    try:
        if photo:
            await message.answer_photo(photo, caption=text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)

        confirm_cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_mailing"),
                    InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_mailing")
                ]
            ]
        )

        await message.answer("Это предпоказ сообщения. Подтвердите отправку или отмените рассылку.",
                           reply_markup=confirm_cancel_keyboard)
        await state.set_state(Mailing.confirm_mailing)
    except Exception as e:
        logging.error(f"Error in show_preview: {e}")
        await message.answer("Произошла ошибка при создании предпросмотра.",
                           reply_markup=admin_main_keyboard)
        await state.clear()


@mailing.callback_query(Mailing.confirm_mailing, F.data == "confirm_mailing")
async def confirm_mailing_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("message_text", "")
    photo = data.get("photo")
    buttons = data.get("buttons", [])

    if buttons:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button["text"], url=button["url"]) for button in buttons]
        ])
    else:
        markup = None

    success_count = 0
    fail_count = 0
    users = await get_all_users()

    for user in users:
        try:
            if photo:
                await callback.bot.send_photo(user.tg_id, photo, caption=text, reply_markup=markup)
            else:
                await callback.bot.send_message(user.tg_id, text, reply_markup=markup)
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to send message to {user.tg_id}: {e}")
            fail_count += 1

    status_message = f"Рассылка завершена.\nУспешно отправлено: {success_count}\nОшибок: {fail_count}"
    await callback.message.answer(status_message, reply_markup=admin_main_keyboard)
    await state.clear()
    await callback.answer()


@mailing.callback_query(F.data == "cancel_mailing")
async def cancel_mailing_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Рассылка отменена.", reply_markup=admin_main_keyboard)
    await callback.answer()


@mailing.message(F.text == "Назад🔙")
async def go_back(message: Message, state: FSMContext):
    data = await state.get_data()
    previous_state = data.get("previous_state")

    if previous_state:
        await save_current_state(state)
        await state.set_state(previous_state)
        current_step_message = {
            Mailing.waiting_for_message: "Отправьте сообщение для рассылки или нажмите 'Пропустить'.",
            Mailing.waiting_for_photo: "Отправьте фото для рассылки или напишите 'Пропустить'.",
            Mailing.waiting_for_button_text: "Отправьте текст для кнопки или напишите 'Пропустить'.",
            Mailing.waiting_for_button_url: "Отправьте URL для кнопки."
        }.get(previous_state, "Вернулись к предыдущему шагу.")

        await message.answer(current_step_message, reply_markup=back_exit_keyboard)
    else:
        await message.answer("Нельзя вернуться назад.", reply_markup=admin_main_keyboard)
        await state.clear()