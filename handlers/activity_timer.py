"""
модуль для отслеживания активности пользователя в боте
содержит класс для управления таймерами и проверки, что пользователь не забыл про бота
"""

import asyncio
import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import ContentState

logger = logging.getLogger(__name__)


class ActivityTimerManager:
    """
    менеджер активности пользователей в боте
    следит за тем, чтобы пользователь не оставался в неактивном состоянии слишком долго
    отправляет сообщение с вопросом о продолжении работы после заданного времени
    """

    def __init__(self, delay_seconds: int = 120):
        """
        инициализация менеджера таймеров активности

        Args:
            delay_seconds: время в секундах бездействия, после которого отправляется напоминание
        """
        self._delay = delay_seconds
        # словарь с таймерами для каждого пользователя
        self._timers: dict[int, asyncio.Task] = {}
        # словарь с id сообщений-напоминаний для возможности их удаления
        self._messages: dict[int, int] = {}

    async def start(self, user_id: int, state: FSMContext, bot: Bot) -> None:
        """
        запускает таймер активности для пользователя

        Args:
            user_id: идентификатор пользователя
            state: состояние FSM пользователя
            bot: экземпляр бота для отправки сообщений
        Returns:
            None
        """
        # сначала отменяем любой существующий таймер для этого пользователя (на всякий)
        self.cancel(user_id)

        async def check_activity():
            """
            функция проверки активности, которая выполняется после истечения таймера
            отправляет сообщение с вопросом, продолжает ли пользователь изучать материал
            """
            try:
                # ждем указанное время (заданное в delay, в секундах)
                await asyncio.sleep(self._delay)
                # проверяем текущее состояние пользователя
                current_state = await state.get_state()

                # проверяем только пользователей, которые находятся в режиме просмотра контента
                # (т.е. в выборе предмета, подтемы, скроллинге подтемы)
                if current_state in [
                    ContentState.IN_TOPICS.state,
                    ContentState.IN_LECTURE.state,
                ]:
                    # удаляем предыдущее сообщение о проверке активности, если оно было (чтобы было тольо 1)
                    old_msg_id = self._messages.get(user_id)
                    if old_msg_id:
                        await bot.delete_message(user_id, old_msg_id)

                    # отправляем новое сообщение с вопросом о продолжении работы
                    msg = await bot.send_message(
                        user_id,
                        "Привет! Ты еще изучаешь материал?",
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="Да", callback_data="still_learning"
                                    ),
                                    InlineKeyboardButton(
                                        text="Нет, верни в начало",
                                        callback_data="return_to_menu",
                                    ),
                                ]
                            ]
                        ),
                        parse_mode="HTML",
                    )
                    self._messages[user_id] = msg.message_id

            except asyncio.CancelledError:
                # обработка отмены таймера - ничего не делаем, просто выходим
                pass
            except Exception as e:
                logger.error(f"ошибка в таймере активности: {e}")
            finally:
                # в любом случае убираем таймер из словаря после его срабатывания
                self._timers.pop(user_id, None)

        # создаем новую задачу и сохраняем ее в словаре таймеров
        task = asyncio.create_task(check_activity())
        self._timers[user_id] = task

    def cancel(self, user_id: int):
        """
        отменяет таймер активности для указанного пользователя

        Args:
            user_id: идентификатор пользователя
        """
        task = self._timers.pop(user_id, None)
        if task:
            task.cancel()

    def forget_message(self, user_id: int):
        """
        удаляет информацию о сообщении с проверкой активности

        Args:
            user_id: идентификатор пользователя
        """
        self._messages.pop(user_id, None)

    def reset(self, user_id: int):
        """
        полностью сбрасывает все данные о таймере активности пользователя
        отменяет таймер и удаляет информацию о сообщении

        Args:
            user_id: идентификатор пользователя
        """
        self.cancel(user_id)
        self.forget_message(user_id)


activity_timer = ActivityTimerManager()
