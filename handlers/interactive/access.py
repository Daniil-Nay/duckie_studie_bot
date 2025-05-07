"""
Данный модуль предназначен для управления интерактивным режимом,
 с целью ограничения доступа до 1 человека одновременно. 
Attributes:
    InteractiveUser: класс для хранения информации о пользователе в интерактивном режиме
    InteractiveState: класс для управления состоянием интерактивного режима
"""

from dataclasses import dataclass
import asyncio


@dataclass
class InteractiveUser:
    """
    Класс для хранения информации о пользователе в интерактивном режиме
    Attributes:
        user_id: ID пользователя
        chat_id: ID чата
        lock: asyncio.Lock
    """

    user_id: int
    chat_id: int
    lock: asyncio.Lock


class InteractiveState:
    """
    Класс для управления состоянием интерактивного режима
    Attributes:
        _active_user: информация о активном пользователе
        _global_lock: asyncio.Lock
    """

    def __init__(self):
        self._active_user: InteractiveUser | None = None
        self._global_lock = asyncio.Lock()

    async def try_acquire_interactive(self, user_id: int, chat_id: int) -> bool:
        """
        Попытка захватить интерактивный режим
        (если пользователь пробует зайи в иинтераткивный режим)

        Args:
            user_id: ID пользователя
            chat_id: ID чата

        Returns:
            bool: True если удалось захватить, False если режим занят
        """
        async with self._global_lock:
            if self._active_user is None:
                self._active_user = InteractiveUser(
                    user_id=user_id, chat_id=chat_id, lock=asyncio.Lock()
                )
                return True
            return self._active_user.user_id == user_id

    async def release_interactive(self, user_id: int) -> bool:
        """
        Освобождение интерактивного режима

        Args:
            user_id: ID пользователя

        Returns:
            bool: True если режим был освобожден, False если не было прав
        """
        async with self._global_lock:
            if self._active_user and self._active_user.user_id == user_id:
                self._active_user = None
                return True
            return False

    def get_active_user(self) -> InteractiveUser | None:
        """
        Получить информацию об активном пользователе

        Returns:
            InteractiveUser | None: информация об активном пользователе или None
        """
        return self._active_user


interactive_state = InteractiveState()