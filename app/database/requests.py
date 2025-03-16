import random
import logging
from app.database.models import async_session
from app.database.models import User, Order, Rate, Support, Wallet
from sqlalchemy import select, update, delete, desc, func
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from datetime import datetime


async def set_user(tg_id, username=None, full_name=None):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            return True
        else:
            # Добавляем пользователя с tg_id, username и full_name
            new_user = User(
                tg_id=tg_id,
                username=username,
                full_name=full_name
            )
            session.add(new_user)
            await session.commit()
            return False


# Функция для обновления данных пользователя
async def update_user_data(tg_id, field, value):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == tg_id).values({field: value})
        )
        await session.commit()


async def get_user_info(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            return {
                "tg_id": user.tg_id,
                "username": user.username,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "nickname": user.nickname,
                "bank_card": user.bank_card,
            }
        return None  # Если пользователь не найден


# Изменение никнейма в профиле
async def update_nickname(tg_id, new_nickname):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.nickname = new_nickname
            await session.commit()


# Изменение банковской карты в профиле
async def update_bank_card(tg_id, new_bank_card):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.bank_card = new_bank_card
            await session.commit()


# Функция для получения всех кошельков из таблицы Wallets
async def get_wallets():
    async with async_session() as session:
        result = await session.execute(select(Wallet))
        wallets = result.scalars().all()  # Получаем все кошельки
        return wallets


# Функция для получения текущего значения курса из таблицы Rate
async def get_rate():
    async with async_session() as session:
        rate = await session.scalar(select(Rate.rate_value).where(Rate.id == 1))
        return rate


# Функция для получения контакта поддержки из таблицы Support
async def get_support_contact():
    async with async_session() as session:
        result = await session.scalar(select(Support.support_value).where(Support.id == 1))
        return result


# Функция для обновления курса администратором
async def update_rate(new_rate_value: float):
    async with async_session() as session:
        # Получаем текущую запись с курсом по фиксированному ID
        rate = await session.scalar(select(Rate).where(Rate.id == 1))

        if rate:
            # Обновляем значение курса
            await session.execute(
                update(Rate).where(Rate.id == 1).values(rate_value=new_rate_value)
            )
            await session.commit()
        else:
            # Если записи еще нет, создаем новую
            session.add(Rate(rate_value=new_rate_value))
            await session.commit()


async def update_support_contact(new_support_contact):
    async with async_session() as session:
        try:
            # Получаем текущую запись контакта по фиксированному ID
            contact = await session.scalar(select(Support).where(Support.id == 1))

            if contact:
                # Обновляем контакт
                await session.execute(
                    update(Support).where(Support.id == 1).values(support_value=new_support_contact)
                )
            else:
                # Если записи еще нет, создаем новую
                session.add(Support(id=1, support_value=new_support_contact))

            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при обновлении контакта поддержки: {e}")


async def add_wallet(network: str, address: str):
    async with async_session() as session:
        new_wallet = Wallet(network=network, address=address)
        session.add(new_wallet)
        await session.commit()


async def delete_wallet(wallet_address: str) -> bool:

    try:
        async with async_session() as session:
            # Find the wallet by address
            result = await session.execute(
                select(Wallet).where(Wallet.address == wallet_address)
            )
            wallet = result.scalar_one_or_none()

            if wallet:
                await session.delete(wallet)
                await session.commit()
                return True
            else:
                return False

    except Exception as e:
        logging.error(f"Error deleting wallet: {e}")
        return False


async def create_order(user_id, currency, value, exchange_rate, network, bank_card, wallet):
    async with async_session() as session:
        try:
            new_order = Order(
                user_id=user_id,
                currency=currency,
                value=value,
                exchange_rate=exchange_rate,
                network=network,
                bank_card=bank_card,
                wallet=wallet,
                status='Ожидает оплаты'
            )
            session.add(new_order)
            await session.commit()
            # Обновляем объект new_order после коммита
            await session.refresh(new_order)
            return new_order.id  # Возвращаем ID созданного заказа
        except Exception as e:
            await session.rollback()
            logging.error(f"Error creating order: {e}")
            raise


async def get_order_info(id):
    async with async_session() as session:
        try:
            order = await session.scalar(select(Order).where(Order.id == id))
            if order:
                return {
                    "id": order.id,
                    "user_id": order.user_id,
                    "currency": order.currency,
                    "value": order.value,
                    "exchange_rate": order.exchange_rate,
                    "network": order.network,
                    "bank_card": order.bank_card,
                    "wallet": order.wallet,
                    "status": order.status,
                    "file_id": order.file_id,
                    "date_created": order.date_created,
                    "date_payment": order.date_payment
                }
            logging.warning(f"Order with id {id} not found")
            return None
        except Exception as e:
            logging.error(f"Error getting order info: {e}")
            return None


async def update_order_status(order_id: int, new_status: str, file_id: str = None, payment_date: datetime = None):
    """
    Update order status and file_id in database.

    Args:
        order_id (int): ID of the order to update
        new_status (str): New status for the order
        file_id (str, optional): Telegram file_id of the payment screenshot
        payment_date (datetime, optional): Date and time when payment screenshot was received
    """
    async with async_session() as session:
        try:
            values = {"status": new_status}

            if file_id is not None:
                values["file_id"] = file_id

            if payment_date is not None:
                values["date_payment"] = payment_date

            await session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(**values)
            )
            await session.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating order status: {e}")
            await session.rollback()
            return False


async def get_order_status(id: int) -> str | None:

    async with async_session() as session:
        try:
            status = await session.scalar(
                select(Order.status).where(Order.id == id)
            )
            return status
        except Exception as e:
            logging.error(f"Error getting order status: {e}")
            return None


async def get_orders(offset: int = 0, limit: int = 10):
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Order.id).offset(offset).limit(limit).order_by(Order.date_created.desc())
            )
            orders = result.scalars().all()
            return orders
        except Exception as e:
            logging.error(f"Error fetching orders: {e}")
            return []


async def get_orders_page(page: int = 1, per_page: int = 10) -> List[Order]:
    """
    Получает страницу ордеров из базы данных

    Args:
        page: Номер страницы
        per_page: Количество ордеров на странице

    Returns:
        List[Order]: Список объектов Order для указанной страницы
    """
    async with async_session() as session:
        try:
            skip = (page - 1) * per_page
            query = select(Order).order_by(Order.date_created.desc()).offset(skip).limit(per_page)
            result = await session.scalars(query)
            return list(result)
        except Exception as e:
            logging.error(f"Error getting orders page: {e}")
            return []


async def get_total_orders() -> int:
    """
    Получает общее количество ордеров в базе данных

    Returns:
        int: Общее количество ордеров
    """
    async with async_session() as session:
        try:
            query = select(func.count()).select_from(Order)
            result = await session.scalar(query)
            return result
        except Exception as e:
            logging.error(f"Error getting total orders count: {e}")
            return 0


async def get_orders_page_with_total(page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Получает страницу ордеров вместе с информацией о пагинации

    Args:
        page: Номер страницы
        per_page: Количество ордеров на странице

    Returns:
        Dict с ключами:
            orders: List[Order] - список ордеров
            total: int - общее количество ордеров
            total_pages: int - общее количество страниц
    """
    try:
        logging.info(f"Fetching orders for page {page}")
        orders = await get_orders_page(page, per_page)
        total = await get_total_orders()
        total_pages = (total + per_page - 1) // per_page

        logging.info(f"Found {len(orders)} orders, total pages: {total_pages}")
        return {
            "orders": orders,
            "total": total,
            "total_pages": total_pages
        }
    except Exception as e:
        logging.error(f"Error getting orders page with total: {e}")
        return {
            "orders": [],
            "total": 0,
            "total_pages": 0
        }


async def get_all_users():
    async with async_session() as session:
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()
            return users
        except Exception as e:
            logging.error(f"Error fetching users: {e}")
            return []


async def get_orders_page_for_user(user_id: int, page: int = 1, per_page: int = 10) -> List[Order]:
    """
    Получает страницу ордеров пользователя из базы данных

    Args:
        user_id: ID пользователя (tg_id)
        page: Номер страницы
        per_page: Количество ордеров на странице

    Returns:
        List[Order]: Список объектов Order для указанной страницы
    """
    async with async_session() as session:
        try:
            skip = (page - 1) * per_page
            query = (
                select(Order)
                .where(Order.user_id == user_id)  # Фильтр по user_id
                .order_by(Order.date_created.desc())
                .offset(skip)
                .limit(per_page)
            )
            result = await session.scalars(query)
            return list(result)
        except Exception as e:
            logging.error(f"Error getting orders page for user {user_id}: {e}")
            return []


async def get_total_orders_for_user(user_id: int) -> int:
    """
    Получает общее количество ордеров пользователя в базе данных

    Args:
        user_id: ID пользователя (tg_id)

    Returns:
        int: Общее количество ордеров пользователя
    """
    async with async_session() as session:
        try:
            query = (
                select(func.count())
                .select_from(Order)
                .where(Order.user_id == user_id)  # Фильтр по user_id
            )
            result = await session.scalar(query)
            return result
        except Exception as e:
            logging.error(f"Error getting total orders count for user {user_id}: {e}")
            return 0


async def get_orders_page_with_total_for_user(user_id: int, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Получает страницу ордеров пользователя вместе с информацией о пагинации

    Args:
        user_id: ID пользователя (tg_id)
        page: Номер страницы
        per_page: Количество ордеров на странице

    Returns:
        Dict с ключами:
            orders: List[Order] - список ордеров пользователя
            total: int - общее количество ордеров пользователя
            total_pages: int - общее количество страниц
    """
    try:
        # Заменяем get_orders_page на get_orders_page_for_user
        orders = await get_orders_page_for_user(user_id, page, per_page)
        total = await get_total_orders_for_user(user_id)
        total_pages = (total + per_page - 1) // per_page

        return {
            "orders": orders,
            "total": total,
            "total_pages": total_pages
        }
    except Exception as e:
        logging.error(f"Error getting orders page with total for user {user_id}: {e}")
        return {
            "orders": [],
            "total": 0,
            "total_pages": 0
        }


async def is_profile_complete(tg_id: int) -> bool:
    """Проверяет, заполнены ли все обязательные поля профиля пользователя."""
    user_info = await get_user_info(tg_id)
    if user_info is None:
        return False
    required_fields = ['phone_number', 'nickname', 'bank_card']
    return all(user_info[field] is not None and user_info[field] != '' for field in required_fields)
