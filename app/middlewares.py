# В app/middlewares.py

from aiogram import BaseMiddleware
from aiogram.types import Message
from app.database.requests import is_profile_complete
from app.user_keyboard import phone_button
from app.states import Form


class ProfileCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        tg_id = event.from_user.id
        state = data['state']

        # Пропускаем проверку для состояния регистрации
        current_state = await state.get_state()
        if current_state in [Form.phone_number, Form.nickname, Form.bank_card]:
            return await handler(event, data)

        # Проверяем полноту профиля
        if not await is_profile_complete(tg_id):
            await event.answer(
                "Ваш профиль не заполнен. Пожалуйста, завершите регистрацию, отправив номер телефона.",
                reply_markup=phone_button
            )
            await state.set_state(Form.phone_number)
            return

        return await handler(event, data)