from datetime import datetime

from sqlalchemy import ForeignKey, String, BigInteger, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from config import DB_URL

engine = create_async_engine(url=DB_URL,
                             echo=True)
    
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    nickname: Mapped[str] = mapped_column(String, nullable=True)
    bank_card: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # Связи с заметками и напоминаниями
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=True)
    exchange_rate: Mapped[float] = mapped_column(Float, nullable=True) # Курс по которому создан ордер
    network: Mapped[str] = mapped_column(String, nullable=True)
    bank_card: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wallet: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    tx_id: Mapped[str] = mapped_column(String, nullable=True)
    date_created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="orders")


class Wallet(Base):
    __tablename__ = 'wallets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String, nullable=True)  # Тут записана сеть
    address: Mapped[str] = mapped_column(String, nullable=True)  # Тут записаны кошельки


class Rate(Base):
    __tablename__ = 'rates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)  # Фиксированный ID
    rate_value: Mapped[float] = mapped_column(Float, nullable=True)  # Курс, который будет меняться


class Support(Base):
    __tablename__ = 'support'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)  # Фиксированный ID
    support_value: Mapped[str] = mapped_column(String, nullable=True)  # Тут записан контакт поддержки


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
