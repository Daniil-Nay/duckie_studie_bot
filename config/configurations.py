"""
Данный модуль содержит конфигурацию для бота 
(чувствительные данные лежат в .env файле)
"""

from functools import lru_cache
import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    Искючение которое возникает при ошибках конфигурации
    """


@dataclass
class TgBot:
    """
    Конфигурация для tg бота

    Attributes:
        token: токен для доступа к tg API
        db_path: путь к файлу базы данных
        images_path: путь к директории с изображениями
        videos_path: путь к директории с видео
    """

    token: str
    db_path: str
    images_path: str
    videos_path: str

    def __post_init__(self):
        if not self.token:
            raise ConfigError("Требуется токен для бота")


@dataclass
class LLM:
    """
    Конфигурация для языковой модели (LLM)

    Attributes:
        model_name: название ллм
        device: устройство для инференса (cuda или cpu)
        max_new_tokens: max количество токенов в ответе
        temperature: температура генерации
        top_p:  nucleus sampling
        repetition_penalty: штраф за повтор
        timeout_seconds: таймаут запроса в сек
        num_retries: колво попыток при ошибке
        error_message: сообщ при ошибке LLM
        timeout_message: сообщ при таймауте
    """

    model_name: str
    device: str
    max_new_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    timeout_seconds: int
    num_retries: int
    error_message: str
    timeout_message: str


@dataclass
class Config:
    """
    Основной класс конфигурации приложения

    Attributes:
        tg_bot: конфигурация tg бота
        llm: конфигурация языковой модели
    """

    tg_bot: TgBot
    llm: LLM


@lru_cache(maxsize=1)
def load_config() -> Config:
    """
    Загружает конфигурацию из .env файла

    Returns:
        Config: объект конфигурации приложения

    Raises:
        ConfigError: если отсутствует обязательная конфигурация
    """
    if load_dotenv():
        logger.info("загружаем конфигурацию из .env файла")
    try:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if os.getenv("LLM_DEVICE"):
            device = os.getenv("LLM_DEVICE")

        config: Config = Config(
            tg_bot=TgBot(
                token=os.getenv("BOT_TOKEN", ""),
                db_path=os.getenv("DB_PATH", "database/bot_content.db"),
                images_path=os.getenv("IMAGES_PATH", "images"),
                videos_path=os.getenv("VIDEOS_PATH", "videos"),
            ),
            llm=LLM(
                model_name=os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct"),
                device=device,
                max_new_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                top_p=float(os.getenv("LLM_TOP_P", "0.95")),
                repetition_penalty=float(os.getenv("LLM_REPETITION_PENALTY", "1.2")),
                timeout_seconds=int(os.getenv("LLM_TIMEOUT", "900")),
                num_retries=int(os.getenv("LLM_RETRIES", "1")),
                error_message=os.getenv(
                    "LLM_ERROR_MESSAGE",
                    "Извини, Duckie сейчас недоступен. Пожалуйста, попробуй позже.",
                ),
                timeout_message=os.getenv(
                    "LLM_TIMEOUT_MESSAGE",
                    "Извини, запрос занял слишком много времени. Пожалуйста, попробуй позже или задай более простой вопрос.",
                ),
            ),
        )
        logger.info("конфигурация загружена успешно")
        logger.debug("путь к базе данных: %s", config.tg_bot.db_path)
        logger.debug("путь к папке с изображениями: %s", config.tg_bot.images_path)
        logger.debug("путь к папке с видео: %s", config.tg_bot.videos_path)
        logger.debug("модель LLM: %s на %s", config.llm.model_name, config.llm.device)
        return config
    except ConfigError as e:
        logger.error("ошибка конфигурации: %s", str(e))
        raise
