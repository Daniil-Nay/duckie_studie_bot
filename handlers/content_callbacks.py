"""
модуль обработки callback-запросов для контентной части бота
"""

import logging
import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from states import ContentState
from handlers.activity_timer import activity_timer
from keyboards.keyboards import keyboard_manager
from storage import user_original_messages
from utils.media import send_menu_content

logger = logging.getLogger(__name__)
router = Router()


async def update_user_state(callback_data: str, state: FSMContext) -> None:
    """этот метод устанавливает состояние пользователя на основе выбранного раздела
    Args:
        callback_data: строка с данными callback-запроса
        state: контекст FSM для управления состоянием
    Returns:
        None
    """
    if callback_data == "start":
        await state.set_state(ContentState.IN_MENU)
    elif callback_data in ["linear_algebra", "geometry", "calculus"]:
        await state.set_state(ContentState.IN_TOPICS)
    elif "matrix" in callback_data or "vector" in callback_data:
        await state.set_state(ContentState.IN_LECTURE)


async def find_media_file(media_path: str) -> str:
    """метод для нахождения пути  к медиафайлу
    Args:
        media_path: путь к медиафайлу (может быть относительным или абсолютным)
    Returns:
        str: полный путь к найденному файлу или None если файл не найден
    """

    if not media_path:
        return None

    path = media_path.replace("\\", "/")
    path = path.replace("../", "").replace("./", "")

    filename = os.path.basename(path)

    standard_path = os.path.join("content", "images", filename)
    if os.path.exists(standard_path):
        return standard_path

    alt_path = os.path.join("images", filename)
    if os.path.exists(alt_path):
        return alt_path

    logger.error(f"файл не найден: {media_path}")
    return None


@router.callback_query(F.data == "still_learning")
async def handle_still_learning(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """метод-обработчик ответа 'Да' на вопрос о продолжении обучения

    Args:
        callback: объект callback-запроса
        state: контекст FSM для управления состоянием
        bot: объект бота для отправки сообщений

    Returns:
        None
    """
    user_id = callback.from_user.id
    await callback.message.delete()
    await activity_timer.start(user_id, state, bot)
    await callback.answer()


@router.callback_query(F.data == "return_to_menu")
async def handle_return_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """метод-обработчик для возврата в главное меню

    Args:
        callback: объект callback-запроса
        state: контекст FSM для управления состоянием

    Returns:
        None
    """
    user_id = callback.from_user.id
    await callback.message.delete()
    await state.clear()
    text, kb = keyboard_manager.get_keyboard("start")
    msg = await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    user_original_messages[user_id] = msg.message_id
    await callback.answer()


@router.callback_query()
async def handle_content(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """основной обработчик callback-запросов по контенту:

    Обрабатывает навигацию по меню и контенту бота.
    При обычной навигации происходит редактирование существующего сообщения,
    а при навигации по теории (кнопки Далее/Назад) отправляется новое сообщение с контентом.
    Args:
        callback: объект callback-запроса от пользователя
        state: контекст FSM для управления состоянием
        bot: объект бота для отправки сообщений

    Returns:
        None
    """
    user_id = callback.from_user.id
    callback_data = callback.data

    # пропускаем обработку интерактивного режима (т.к. это отдельный режим)
    if callback_data == "interactive":
        return

    # получаем данные меню по callback_data
    menu = keyboard_manager.get_menu(callback_data)
    if not menu:
        await callback.answer(
            "контент недоступен: возможно, нет теории в данной подтеме"
        )
        return

    await update_user_state(callback_data, state)

    # проверка, является ли это навигацией по теории (т.е. кнопки Далее/Назад)
    is_theory_navigation = any(
        button[0] in ["➡️ Далее", "⬅️ Назад"]
        for button in keyboard_manager.get_buttons(callback_data)
    )

    if not is_theory_navigation:
        # Для обычной навигации  редачим существующее сообщение
        try:
            msg = await callback.message.edit_text(
                text=menu["text"], reply_markup=menu["keyboard"], parse_mode="HTML"
            )
            user_original_messages[user_id] = msg.message_id
            await callback.answer()

            # запускаем таймер активности (acitivity_timer) если пользователь в режиме просмотра контента
            current_state = await state.get_state()
            if current_state in [
                ContentState.IN_TOPICS.state,
                ContentState.IN_LECTURE.state,
            ]:
                await activity_timer.start(user_id, state, bot)
            return
        except:
            await callback.message.delete()
    else:
        # Для удаления клавы со старого сообщения
        await callback.message.edit_reply_markup(reply_markup=None)

    msg = await send_menu_content(callback.message, menu)
    user_original_messages[user_id] = msg.message_id
    await callback.answer()

    current_state = await state.get_state()
    if current_state in [ContentState.IN_TOPICS.state, ContentState.IN_LECTURE.state]:
        # Примечание (NOTICE): таймер активности запускается в двух местах:
        # 1. выше в блоке "if not is_theory_navigation" для обычной навигации
        # 2. здесь для навигации по теории (кнопки Далее/Назад)
        # т.е. это не дублирование, а обработка двух разных путей выполнения кода
        await activity_timer.start(user_id, state, bot)
