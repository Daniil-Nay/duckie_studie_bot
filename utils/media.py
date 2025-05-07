"""
модуль для работы с медиа-контентом
"""

import os
import logging
from aiogram.types import Message, FSInputFile

logger = logging.getLogger(__name__)


def check_file_exists(path: str) -> bool:
    """
    проверяет существование файла и возможность его открытия

    Args:
        path: путь к файлу

    Returns:
        bool: True если файл существует и доступен, иначе False
    """
    if not path:
        return False

    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                # пробуем прочитать первый байт для проверки доступности
                f.read(1)
            return True
    except Exception as e:
        logger.error(f"ошибка проверки файла {path}: {e}")
    return False


async def send_menu_content(message: Message, menu: dict) -> Message:
    """
    отправка медиа-контента (изображения или видео) или fallback-текста
    1) обеспечивает единый интерфейс для отправки разных типов контента
    2) автоматически предоставляет текстовую альтернативу при невозможности отправить медиа

    Args:
        message: сообщение для ответа
        menu: словарь с данными меню

    Returns:
        Message: отправленное сообщение
    """
    image_path = menu.get("image")
    video_path = menu.get("video")

    try:
        if image_path and check_file_exists(image_path):
            logger.info(f"отправка изображения: {image_path}")
            try:
                photo = FSInputFile(image_path)
                return await message.answer_photo(
                    photo=photo,
                    caption=menu["text"],
                    reply_markup=menu["keyboard"],
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"ошибка при отправке изображения {image_path}: {e}")

        elif video_path and check_file_exists(video_path):
            logger.info(f"отправка видео: {video_path}")
            try:
                video = FSInputFile(video_path)
                return await message.answer_video(
                    video=video,
                    caption=menu["text"],
                    reply_markup=menu["keyboard"],
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"ошибка при отправке видео {video_path}: {e}")

        # NOTICE если медиа отсутствует или не удалось отправить, то отправляем текст просто
        if image_path or video_path:
            logger.warning(
                f"медиафайл не найдеН. изображение: {image_path}, видео: {video_path}"
            )
    except Exception as e:
        logger.error(f"ошибка обработки медиа-контента: {e}")

    logger.info("отправка текстового сообщения как запасной вариант")
    return await message.answer(
        text=menu["text"], reply_markup=menu["keyboard"], parse_mode="HTML"
    )
