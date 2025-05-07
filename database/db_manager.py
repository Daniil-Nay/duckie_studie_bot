"""
Данный модуль преднеазначен для управления базой данных
Предоставляет классы и функции для работы с темами, контентом и навигацией
"""

import sqlite3
from dataclasses import dataclass
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.configurations import Config, load_config


@dataclass
class TopicContent:
    """
    Класс для хранения контента темы предмета

    Attributes:
        text: текстовое содержание темы
        image_path: путь к изображению (опционально)
        video_path: путь к видео (также опционально))
    """

    text: str
    image_path: str | None = None
    video_path: str | None = None


@dataclass
class Topic:
    """
    Класс для представления темы по предмету

    Attributes:
        id: уникальный идентификатор темы
        title: заголовок темы
        content: контент темы
        parent_id: идентификатор родительской темы
    """

    id: int
    title: str
    content: TopicContent
    parent_id: int | None = None


class DatabaseManager:
    """
    Данный класс является менеджером БД для управления контентом бота,
    он обеспечивает работу с темами, контентом и навигацией
    """

    def __init__(self, config: Config):
        """
        Инициализация менеджера БД

        Args:
            config: конфигурация приложения
        """
        self.config = config
        self.conn = sqlite3.connect(config.tg_bot.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """В этом методе происходит инициализация структуры базы данных"""
        self.cursor.executescript(
            """
            -- Таблица тем (разделов)
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                identifier TEXT UNIQUE,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES topics(id)
            );

            -- Таблица контента
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY,
                topic_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                image_path TEXT,
                video_path TEXT,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            );

            -- Таблица навигации (кнопок)
            CREATE TABLE IF NOT EXISTS navigation (
                id INTEGER PRIMARY KEY,
                topic_id INTEGER NOT NULL,
                button_text TEXT NOT NULL,
                target_topic_id INTEGER NOT NULL,
                order_num INTEGER NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topics(id),
                FOREIGN KEY (target_topic_id) REFERENCES topics(id)
            );
        """
        )
        self.conn.commit()

    def add_topic(
        self, title: str, identifier: str | None = None, parent_id: int | None = None
    ) -> int:
        """в этом методе"""
        if identifier is None:
            identifier = title.lower().replace(" ", "_")
        self.cursor.execute(
            "INSERT INTO topics (title, identifier, parent_id) VALUES (?, ?, ?)",
            (title, identifier, parent_id),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def add_content(
        self,
        topic_id: int,
        text: str,
        image_path: str | None = None,
        video_path: str | None = None,
    ) -> int:
        """Метод нужный для добавления контента к теме"""
        if image_path:
            image_path = f"{self.config.tg_bot.images_path}/{image_path}"
        if video_path:
            video_path = f"{self.config.tg_bot.videos_path}/{video_path}"

        self.cursor.execute(
            "INSERT INTO content (topic_id, text, image_path, video_path) VALUES (?, ?, ?, ?)",
            (topic_id, text, image_path, video_path),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def add_navigation(
        self, topic_id: int, button_text: str, target_topic_id: int, order_num: int
    ) -> int:
        """Метод для добавления кнопки навигации"""
        self.cursor.execute(
            """INSERT INTO navigation
               (topic_id, button_text, target_topic_id, order_num)
               VALUES (?, ?, ?, ?)""",
            (topic_id, button_text, target_topic_id, order_num),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_topic_id(self, identifier: str) -> int | None:
        """Метод для получения ID темы по её идентификатору"""
        self.cursor.execute("SELECT id FROM topics WHERE identifier = ?", (identifier,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_topic_content(
        self, topic_identifier: int | str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Метод для получения контента и клавиатуры для темы"""
        if isinstance(topic_identifier, str):
            topic_id = self.get_topic_id(topic_identifier)
            if topic_id is None:
                return "Тема не найдена", InlineKeyboardMarkup(inline_keyboard=[])
        else:
            topic_id = topic_identifier

        self.cursor.execute(
            "SELECT text, image_path, video_path FROM content WHERE topic_id = ?",
            (topic_id,),
        )
        content_row = self.cursor.fetchone()
        if not content_row:
            return "Контент не найден", InlineKeyboardMarkup(inline_keyboard=[])

        text = content_row[0]

        self.cursor.execute(
            """SELECT n.button_text, t.identifier
               FROM navigation n
               JOIN topics t ON n.target_topic_id = t.id
               WHERE n.topic_id = ?
               ORDER BY n.order_num""",
            (topic_id,),
        )
        buttons = self.cursor.fetchall()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button_text, callback_data=target_identifier
                    )
                ]
                for button_text, target_identifier in buttons
            ]
        )

        return text, keyboard

    def get_media_paths(
        self, topic_identifier: int | str
    ) -> tuple[str | None, str | None]:
        """Метод для получения путей к медиафайлам темы"""
        if isinstance(topic_identifier, str):
            topic_id = self.get_topic_id(topic_identifier)
            if topic_id is None:
                return None, None
        else:
            topic_id = topic_identifier

        self.cursor.execute(
            "SELECT image_path, video_path FROM content WHERE topic_id = ?", (topic_id,)
        )
        row = self.cursor.fetchone()
        return (row[0], row[1]) if row else (None, None)

    def get_topic_buttons(self, topic_identifier: int | str) -> list[tuple[str, str]]:
        """Метод для получения списка кнопок для темы"""
        if isinstance(topic_identifier, str):
            topic_id = self.get_topic_id(topic_identifier)
            if topic_id is None:
                return []
        else:
            topic_id = topic_identifier

        self.cursor.execute(
            """SELECT n.button_text, t.identifier
               FROM navigation n
               JOIN topics t ON n.target_topic_id = t.id
               WHERE n.topic_id = ?
               ORDER BY n.order_num""",
            (topic_id,),
        )
        return self.cursor.fetchall()

    def close(self):
        """метод для закрытия соединения с БД"""
        self.conn.close()


db_manager = DatabaseManager(load_config())
