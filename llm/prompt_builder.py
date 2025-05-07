"""
Vодуль для построения промптов для LLM
"""

from llm.system_prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT
from llm.safety_guard import safety_guard
import logging

logger = logging.getLogger(__name__)


def build_prompt(user_input: str, mode: str = "math"):
    """
    создает промпт для LLM с системным контекстом и вводом пользователя
    проверяет безопасность ввода пользователя с помощью safe_guard

    Args:
        user_input: текст от пользователя
        mode: режим работы (math только)

    Returns:
        список сообщений в формате чата
    """
    system_prompt = SYSTEM_PROMPTS.get(mode, DEFAULT_PROMPT)

    if not isinstance(user_input, str):
        user_input = str(user_input)

    # ЗДЕСЬ проверяем безопасность ввода с safe_guard
    safety_result = safety_guard.check(user_input)
    if not safety_result.is_safe:
        logger.warning(
            f"обнаружено нарушение безопасности: {safety_result.violation}, причина: {safety_result.reason}"
        )
        user_input = f"[запрос отклонен системой безопасности] {user_input}"

    # очищаем ввод от потенциально опасных конструкций (html тэги, прочее)
    user_input = safety_guard.sanitize(user_input)

    # Возвращаем простой список из двух сообщений (в  соответствии с структурой длЯ QWEN)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]


def process_response(response: str, system_prompt: str = None) -> str:
    """
    Метод обрабатывает ответ от LLM, удаляя служебные части,
    чтобы пользователю вернуть чистый ответ, без спец токенов от QWEN
    и прочего.

    Args:
        response: ответ от LLM
        system_prompt: системный промпт, который был использован

    Returns:
        обработанный ответ
    """

    if system_prompt and system_prompt in response:
        logger.debug("удаление системного промпта из ответа")
        response = response.replace(system_prompt, "").strip()

    logger.debug("удаление специальных токенов из ответа")
    response = response.replace("<|im_start|>", "").replace("<|im_end|>", "").strip()
    response = response.replace("<|user|>", "").replace("<|assistant|>", "").strip()

    if "<input>" in response and "</input>" in response:
        logger.debug("удаление тегов input из ответа")
        start = response.find("<input>")
        end = response.find("</input>") + len("</input>")
        response = response[:start] + response[end:]

    last_dot = response.rfind(".")
    if last_dot != -1 and last_dot > len(response) // 2:
        logger.debug(f"обрезка ответа на последней точке (поз {last_dot})")
        response = response[: last_dot + 1].strip()

    if not response or len(response) < 10:
        logger.warning("ответ слишком короткий после очистки")
        return "Извини, я не смог сгенерировать подходящий ответ. Попробуйте переформулировать вопрос."

    return response
