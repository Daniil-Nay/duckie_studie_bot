"""
Состояния FSM для интерактивного режима бота
"""

from aiogram.fsm.state import State, StatesGroup


class InteractiveMode(StatesGroup):
    chatting = State()
