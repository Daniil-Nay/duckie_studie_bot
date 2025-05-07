"""
Состояния FSM для навигации по контенту бота
"""

from aiogram.fsm.state import State, StatesGroup


class ContentState(StatesGroup):
    IN_MENU = State()
    IN_TOPICS = State()
    IN_LECTURE = State()
