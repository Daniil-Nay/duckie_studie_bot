"""
МПодуль для настройки гиперпараметров ллмки
"""

from config.configurations import load_config


def get_config():
    """
    получение конфигурации LLM из централизованного конфига

    Returns:
        Dict: словарь с конфигурацией LLM
    """
    config = load_config()

    llm_config = {
        "model_name": config.llm.model_name,
        "device": config.llm.device,
        "max_new_tokens": config.llm.max_new_tokens,
        "temperature": config.llm.temperature,
        "top_p": config.llm.top_p,
        "repetition_penalty": config.llm.repetition_penalty,
        "timeout_seconds": config.llm.timeout_seconds,
        "num_retries": config.llm.num_retries,
        "error_message": config.llm.error_message,
        "timeout_message": config.llm.timeout_message,
    }

    return llm_config
