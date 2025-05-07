"""
модуль с основными обработчиками команд бота
содержит хэндлеры для стартовых команд и общей навигации (т.е. команды /start и /help)
"""
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards.keyboards import keyboard_manager
from storage import user_original_messages
from handlers.activity_timer import activity_timer

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    обработчик команды /start
    сбрасывает состояние пользователя и показывает стартовое меню (клавиатуру)

    Args:
        message: сообщение пользователя
        state: состояние FSM пользователя
    """
    user_id = message.from_user.id
    activity_timer.reset(user_id)
    await state.clear()
    # клавиатура для стартового меню
    text, kb = keyboard_manager.get_keyboard("start")
    msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    user_original_messages[user_id] = msg.message_id


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    обработчик команды /help
    показывает пользователю справочную информацию о боте (два доступных режима и мини описание бота)

    Args:
        message: сообщение пользователя
    """
    text, kb = keyboard_manager.get_keyboard("help")
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
