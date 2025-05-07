"""
модуль для управления клавиатурами бота
предоставляет функционал для работы с интерактивными клавиатурами и меню
отвечает только за построение UI, не за получение данных
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.menu_loader import menu_loader


class KeyboardManager:
    """
    менеджер клавиатуры для создания и управления интерактивными клавиатурами.
    Он нужен для моего бота по нескольким причинам:
    1) создан для отделения UI от логики получения данных
    2) решает проблему повторного использования кода клавиатур (самое важное)
    3) позволяет централизованно управлять форматированием и стилем всех клавиатур бота
    """

    def build_keyboard(self, buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
        """
        построение клавиатуры из списка кнопок

        Args:
            buttons: список кнопок в формате (текст, callback_data)

        Returns:
            InlineKeyboardMarkup: построенная клавиатура
        """
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
                for button_text, callback_data in buttons
            ]
        )

    def get_keyboard(self, topic_id: str) -> tuple[str, InlineKeyboardMarkup]:
        """
        получение текста и клавиатуры для темы предмета

        Args:
            topic_id: идентификатор темы

        Returns:
            tuple: текст и клавиатура для темы
        """
        text, buttons = menu_loader.get_topic_content(topic_id)
        keyboard = self.build_keyboard(buttons)
        return text, keyboard

    def get_menu(self, topic_id: str) -> dict:
        """
        получение всех данных меню, включая медиафайлы

        Args:
            topic_id: идентификатор темы

        Returns:
            dict: словарь с данными меню (текст, клавиатуру и пути к медиафайлам)
        """
        menu_data = menu_loader.get_menu_data(topic_id)

        # Преобразуем список кнопок в клавиатуру для tg
        keyboard = self.build_keyboard(menu_data.pop("buttons"))

        # ввозвращаем данные с клавиатурой вместо списка кнопок
        return {
            "text": menu_data["text"],
            "keyboard": keyboard,
            **{k: v for k, v in menu_data.items() if k not in ["text", "buttons"]},
        }

    def get_buttons(self, topic_id: str) -> list[tuple[str, str]]:
        """
        получение списка кнопок для темы предмета

        Args:
            topic_id: идентификатор темы

        Returns:
            list: список кортежей (текст кнопки, callback_data)
        """
        return menu_loader.get_buttons(topic_id)


keyboard_manager = KeyboardManager()
