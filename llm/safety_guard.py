"""
модуль безопасности для LLM
объединяет проверки на prompt injection, запретные темы и модерацию контента
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyViolation(Enum):
    """типы нарушений безопасности (которые выявляются)
    Prompt injection вставки
    Лик системного промпта
    Запретные темы
    Спам
    """

    PROMPT_INJECTION = "prompt_injection"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    FORBIDDEN_TOPIC = "forbidden_topic"
    SPAM = "spam"


@dataclass
class SafetyCheckResult:
    """результат проверки безопасности

    при выявлении нарушения безопасности:
    is_safe устанавливается в False

    violation содержит тип нарушения (PROMPT_INJECTION, SYSTEM_PROMPT_LEAK и т.д.)

    reason содержит понятное пользователю объяснение причины отклонения

    details содержит технические детали нарушения (паттерн, тему и т.д.)

    при успешной проверке:
    is_safe = True
    остальные поля остаются пустыми
    """

    is_safe: bool
    violation: SafetyViolation | None = None
    reason: str = ""
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


# по сути сюда можно закидывать разные вариации, в т.ч. и на английском, но для MVP мне казалось
# достаточным
INJECTION_PATTERNS = [
    r"игнорируй предыдущие инструкции",
    r"забудь предыдущие инструкции",
    r"забудь свои инструкции",
    r"проигнорируй свои инструкции",
    r"теперь ты",
    r"ты теперь",
    r"ты должен теперь",
    r"системный промпт",
    r"игнорируй вышеуказанное",
    r"не обращай внимания на предыдущее",
    r"роль:",
    r"ассистент:",
    r"пользователь:",
    r"система:",
    r"твои инструкции",
    r"твои правила",
    r"твой промпт",
    r"твоя система",
    r"твоя конфигурация",
    r"твои настройки",
    r"твоя роль",
    r"твоя личность",
    r"твоя цель",
    r"твоя задача",
    r"твоя работа",
    r"твоя функция",
    r"переключись в режим",
    r"измени свой режим",
    r"выйди из роли",
]

SYSTEM_PROMPT_PATTERNS = [
    r"системный промпт",
    r"system prompt",
    r"твои инструкции",
    r"твои правила",
    r"твои настройки",
    r"твоя роль",
    r"твоя задача",
    r"твоя функция",
    r"твоя конфигурация",
    r"твоя идентичность",
    r"твоя цель",
    r"твоя работа",
    r"как ты работаешь",
    r"как ты устроен",
    r"как ты функционируешь",
    r"какие у тебя инструкции",
    r"какие у тебя правила",
    r"какие у тебя настройки",
    r"какая у тебя роль",
    r"какая у тебя задача",
    r"какая у тебя функция",
    r"какая у тебя конфигурация",
    r"какая у тебя идентичность",
    r"какая у тебя цель",
    r"какая у тебя работа",
]

FORBIDDEN_TOPICS = [
    "наркотики",
    "оружие",
    "взрывчатка",
    "взрывы",
    "терроризм",
    "экстремизм",
    "насилие",
    "самоубийство",
    "расизм",
    "нацизм",
    "фашизм",
    "дискриминация",
    "пропаганда",
    "манипуляция",
    "обход",
    "взлом",
    "хакерство",
    "кража",
    "мошенничество",
]


SPAM_PATTERNS = [
    r"купить",
    r"продать",
    r"заказать",
    r"скидка",
    r"акция",
    r"распродажа",
    r"бесплатно",
    r"заработок",
    r"инвестиции",
    r"криптовалюта",
    r"биткоин",
    r"майнинг",
    r"казино",
    r"ставки",
    r"лотерея",
]


class SafetyGuard:
    """класс для проверки безопасности текста
    Содержит несколько циклов с проверкой на различные темы
    """

    @staticmethod
    def check(text: str) -> SafetyCheckResult:
        """
        проверяет текст на безопасность

        Args:
            text: текст для проверки

        Returns:
            результат проверки
        """
        text = text.lower()

        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"обнаружена попытка prompt injection: {pattern}")
                return SafetyCheckResult(
                    is_safe=False,
                    violation=SafetyViolation.PROMPT_INJECTION,
                    reason="Извини, но я не могу обработать этот запрос.",
                    details={"pattern": pattern},
                )

        for pattern in SYSTEM_PROMPT_PATTERNS:
            if re.search(pattern, text):
                logger.warning(
                    f"Ообнаружена попытка получить системный промпт: {pattern}"
                )
                return SafetyCheckResult(
                    is_safe=False,
                    violation=SafetyViolation.SYSTEM_PROMPT_LEAK,
                    reason="Извини, но я не могу раскрыть эту информацию.",
                    details={"pattern": pattern},
                )

        for topic in FORBIDDEN_TOPICS:
            if topic in text:
                logger.warning(f"обнаружена запретная тема: {topic}")
                return SafetyCheckResult(
                    is_safe=False,
                    violation=SafetyViolation.FORBIDDEN_TOPIC,
                    reason="Извини, но я не могу обсуждать эту тему.",
                    details={"topic": topic},
                )

        for pattern in SPAM_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"обнаружен спам: {pattern}")
                return SafetyCheckResult(
                    is_safe=False,
                    violation=SafetyViolation.SPAM,
                    reason="Извини, но я не могу обработать этот запрос.",
                    details={"pattern": pattern},
                )

        return SafetyCheckResult(is_safe=True)

    @staticmethod
    def sanitize(text: str) -> str:
        """
        Я добавил эту функцию для защиты от потенциально опасных конструкций в тексте.
        Она удаляет HTML-теги, которые могут содержать вредоносный код,
        специальные токены, которые могут повлиять на работу модели,
        нормализует пробелы для предотвращения атак через форматирование.


        Args:
            text: входной текст для очистки

        Returns:
            очищенный текст
        """
        text = re.sub(r"<[^>]+>", "", text)

        text = re.sub(r"<\|.*?\|>", "", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()


safety_guard = SafetyGuard()
