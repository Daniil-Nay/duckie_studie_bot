"""
модуль для загрузки данных меню из базы данных
отделяет логику получения данных от построения UI
"""

from database.db_manager import db_manager


class MenuLoader:
    """
    загрузчик данных меню из базы данных
    """

    def __init__(self, db_manager):
        """
        инициализация загрузчика меню

        Args:
            db_manager: менеджер базы данных
        """
        self.db = db_manager

    def get_topic_content(self, topic_id: str) -> tuple[str, list[tuple[str, str]]]:
        """
        получает текст и список кнопок для темы

        Args:
            topic_id: идентификатор темы

        Returns:
            tuple: текст и список кнопок (текст, callback_data)
        """
        text, _ = self.db.get_topic_content(
            topic_id
        )  # Игнорируем построенную клавиатуру
        buttons = self.db.get_topic_buttons(topic_id)
        return text, buttons

    def get_menu_data(self, topic_id: str) -> dict:
        """
        получает все данные меню для темы, включая медиафайлы

        Args:
            topic_id: идентификатор темы

        Returns:
            dict: словарь с данными меню (текст, кнопки и пути к медиафайлам)
        """
        text, _ = self.db.get_topic_content(topic_id)
        buttons = self.db.get_topic_buttons(topic_id)

        result = {"text": text, "buttons": buttons}

        image_path, video_path = self.db.get_media_paths(topic_id)
        if image_path:
            result["image"] = image_path
        if video_path:
            result["video"] = video_path

        return result

    def get_buttons(self, topic_id: str) -> list[tuple[str, str]]:
        """
        получает список кнопок для темы

        Args:
            topic_id: идентификатор темы

        Returns:
            list: список кортежей (текст кнопки, callback_data)
        """
        return self.db.get_topic_buttons(topic_id)


menu_loader = MenuLoader(db_manager)
