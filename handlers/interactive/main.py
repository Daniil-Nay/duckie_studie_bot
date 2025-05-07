"""
модуль, предназначенный для обработчиков, поддерживающий интерактивный режим бота
взаимодействие с LLM в данном случае обеспечивается с помощью FSM+transformers 
(FSM - finite state machine, контроллирует состояния, в которых находится 
пользователь, взаимодействующий с LLM в данном случае)
"""

import logging

from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext

from keyboards.keyboards import keyboard_manager
from states import InteractiveMode
from .access import interactive_state
from llm.worker import llm_worker
from llm.prompt_builder import build_prompt, process_response
from llm.system_prompts import MATH_PROMPT
from handlers.activity_timer import activity_timer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


r: Router = Router(name="interactive_mode")


EXIT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Выйти из интерактивного режима")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


@r.callback_query(F.data == "interactive")
async def enter_interactive_mode(callback: CallbackQuery, state: FSMContext) -> None:
    """
    метод для обработки входа в интерактивный режим
    проверяет доступность режима и устанавливает нужное состояние пользователя
    Args:
        callback: callback-запрос
        state: состояние FSM
    Returns:
        None
    """
    logger.info("пользователь %s входит в интерактивный режим", callback.from_user.id)
    logger.info("данные callback-а: %s", callback.data)

    try:
        user_id = callback.from_user.id
        activity_timer.reset(user_id)

        # проверка возможности входа в интерактивный режим (c помощью acquire из access.py)
        can_enter = await interactive_state.try_acquire_interactive(
            callback.from_user.id, callback.message.chat.id
        )

        if not can_enter:
            active_user = interactive_state.get_active_user()
            if active_user and active_user.user_id != callback.from_user.id:
                await callback.answer(
                    "Извиняюсь, но интерактивный режим сейчас занят другим пользователем. "
                    "Пожалуйста, подожди и попробуй позже =)",
                    show_alert=True,
                )
                return

        # устанавливаем FSM состояние чата (chatting)
        await state.set_state(InteractiveMode.chatting)
        current_state = await state.get_state()
        logger.info("текущее состояние после установки: %s", current_state)

        await callback.message.delete()
        await callback.message.answer(
            "Ты вошел в интерактивный режим. Теперь ты можешь общаться с ботом.\n"
            "для выхода нажми кнопку 'Выйти из интерактивного режима'",
            reply_markup=EXIT_KEYBOARD,
        )
    except Exception as e:
        logger.error("ошибка при входе в интерактивный режим: %s", str(e))
    finally:
        try:
            await callback.answer()
        except Exception:
            logger.error("не удалось ответить на callback", exc_info=True)


@r.message(F.text == "Выйти из интерактивного режима", InteractiveMode.chatting)
async def exit_interactive_mode(message: Message, state: FSMContext) -> None:
    """
    обработчик для выхода из интерактивного режима
    освобождает состояние интерактивного режима и возвращает пользователя в главное меню
    Args:
        message: сообщение пользователя
        state: состояние FSM
    Returns:
        None
    """
    user_id = message.from_user.id
    logger.info("пользователь %s выходит из интерактивного режима", user_id)
    # получаем текущее состояние FSM
    current_state = await state.get_state()
    logger.info("текущее состояние перед очисткой: %s", current_state)

    # здесь освобождаем интерактивный режим (с помощью release из access.py)
    await interactive_state.release_interactive(user_id)
    activity_timer.reset(user_id)

    # очищаем (по сути обнуляем состояние FSM для пользователя) и переходим в главное меню.
    await state.clear()
    await message.answer(".", reply_markup=ReplyKeyboardRemove())
    await message.bot.delete_message(
        chat_id=message.chat.id, message_id=message.message_id + 1
    )

    text, kb = keyboard_manager.get_keyboard("start")
    await message.answer(text, reply_markup=kb)
    logger.info("пользователь %s вернулся в главное меню", user_id)


@r.message(InteractiveMode.chatting)
async def process_message(message: Message, state: FSMContext) -> None:
    """
    обработчик сообщений в интерактивном режиме
    принимает сообщение пользователя, отправляет его в LLM и возвращает ответ
    Args:
        message: сообщение пользователя
        state: состояние FSM
    Returns:
        None
    """
    current_state = await state.get_state()
    user_id = message.from_user.id
    logger.info("обработка сообщения. Текущее состояние: %s", current_state)
    logger.info("сообщение от пользователя %s: %s", user_id, message.text)

    # проверяем, что пользователь имеет доступ к интерактивному режиму
    active_user = interactive_state.get_active_user()

    try:
        # показываем пользователю, что бот печатает (хотя ограничения у TG API есть, но мы их обходим с помощью
        # блока интарктивного режима для 1 пользователя, т.е. больше чаттиться одноврепменно не могут)
        await message.bot.send_chat_action(
            chat_id=message.from_user.id, action="typing"
        )

        # формируем промпт и отправляем запрос к LLM
        prompt = build_prompt(message.text, mode="math")
        logger.info("отправка запроса к LLM...")

        answer = await llm_worker.generate_response(prompt)
        answer = process_response(answer, MATH_PROMPT)

        logger.info("ответ сгенерирован, отправляем пользователю")
        await message.answer(answer)
        logger.info("ответ отправлен")

    except Exception as e:
        logger.error("ошибка при обработке сообщения: %s", str(e), exc_info=True)
        await message.answer(
            "извини, произошла ошибка при обработке твоего сообщения. "
            "попробуй еще раз."
        )
