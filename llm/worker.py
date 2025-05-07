"""
модуль для обработки запросов к LLM в отдельном процессе
отвечает за инициализацию модели, обработку запросов и генерацию ответов
"""

import multiprocessing
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
import asyncio
import time
import json
import os
from datetime import datetime
import re

from llm.settings import get_config
from llm.prompt_builder import build_prompt, process_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_llm_interaction(prompt, response, duration, error=None):
    """
    логирование взаимодействия с LLM

    Args:
        prompt: запрос к модели
        response: ответ модели
        duration: время обработки в секундах
        error: описание ошибки, если возникла
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "duration": f"{duration:.2f}s",
        "error": error,
    }

    try:
        os.makedirs("logs", exist_ok=True)

        log_file = f"logs/llm_interactions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    except Exception as e:
        logger.error(f"ошибка записи лога взаимодействия с LLM: {e}")


def log_raw_response(prompt, raw_response, cleaned_response):
    """
    логирование сырого ответа модели (создаю здесь директорию, мне это было важно
    для отладки)

    Args:
        prompt: запрос к модели
        raw_response: необработанный ответ модели
        cleaned_response: обработанный ответ модели
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "raw_response": raw_response,
        "cleaned_response": cleaned_response,
    }

    try:
        os.makedirs("logs", exist_ok=True)

        log_file = f"logs/llm_raw_responses_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    except Exception as e:
        logger.error(f"ошибка записи лога ответа модели: {e}")


class LLMWorker:
    """
    воркер для обработки запросов к LLM в отдельном процессе

    он обеспечисвет  загрузку модели, обработку запросов в отдельном процессе,
    обработку ошибок и асинхронную генерацию ответов
    """

    def __init__(self):
        """
        инициализация воркера LLM
        """
        self.model = None
        self.tokenizer = None
        self.request_queue = multiprocessing.Queue()
        self.response_queue = multiprocessing.Queue()
        self.process = None
        self.config = get_config()
        self.model_initialized = False

    def init_model(self):
        """
        инициализация модели с обработкой ошибок

        Returns:
            bool: True если модель успешно инициализирована, False в случае ошибки
        """
        if self.model is not None:
            logger.info("модель уже инициализирована!")
            return True

        try:
            logger.info(
                "инициализация модели %s на %s...",
                self.config["model_name"],
                self.config["device"],
            )

            # проверяю доступность cuda
            if (
                self.config["device"].startswith("cuda")
                and not torch.cuda.is_available()
            ):
                logger.warning("CUDA запрошена, но недоступна. Переход на CPU.")
                self.config["device"] = "cpu"

            if torch.cuda.is_available():
                gpu_info = (
                    f"CUDA {torch.version.cuda}, GPU: {torch.cuda.get_device_name(0)}"
                )
                logger.info(f"CUDA доступна: {gpu_info}")
                logger.info(
                    f"Память GPU: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB"
                )
            else:
                logger.info("CUDA недоступна, переход на CPU")

            logger.info("загрузка токенизатора...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config["model_name"], trust_remote_code=True
            )

            logger.info("загрузка модели...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config["model_name"],
                device_map=self.config["device"],
                torch_dtype=torch.float16,
                trust_remote_code=True,
            )

            logger.info("модель успешно инициализирована на %s", self.config["device"])
            self.model_initialized = True
            return True

        except Exception as e:
            logger.error("ошибка инициализации модели: %s", str(e), exc_info=True)
            self.model_initialized = False
            return False

    def process_requests(self):
        """
        основной цикл обработки запросов с обработкой ошибок
        """
        model_ready = self.init_model()

        while True:
            try:
                prompt = self.request_queue.get()
                start_time = time.time()
                logger.info("получен запрос на обработку")

                if prompt == "STOP":
                    break

                if not model_ready:
                    error_msg = "модель не инициализирована"
                    logger.error(f"{error_msg}, возвращаем запасное сообщение")
                    response = self.config["error_message"]
                    log_llm_interaction(
                        prompt, response, time.time() - start_time, error_msg
                    )
                    self.response_queue.put(f"FALLBACK: {response}")
                    continue

                chat_messages = build_prompt(prompt)
                logger.info(f"созданы сообщения для чата: {chat_messages}")

                text = self.tokenizer.apply_chat_template(
                    chat_messages, tokenize=False, add_generation_prompt=True
                )

                logger.info(f"обработка запроса: {text[:100]}...")

                logger.info("токенизация ввода...")
                tokens = self.tokenizer(text, return_tensors="pt").to(
                    self.config["device"]
                )

                logger.info("генерация ответа...")
                with torch.no_grad():
                    output = self.model.generate(
                        **tokens,
                        max_new_tokens=self.config["max_new_tokens"],
                        temperature=self.config["temperature"],
                        top_p=self.config["top_p"],
                        repetition_penalty=self.config["repetition_penalty"],
                        do_sample=True,
                    )

                output_tokens = len(output[0]) - len(tokens.input_ids[0])

                result = self.tokenizer.decode(output[0], skip_special_tokens=True)

                input_text_len = len(result) - len(
                    self.tokenizer.decode(
                        output[0][len(tokens.input_ids[0]) :], skip_special_tokens=True
                    )
                )

                raw_answer = result[input_text_len:].strip()

                answer = process_response(raw_answer)

                log_raw_response(text, raw_answer, answer)

                duration = time.time() - start_time

                logger.info(
                    f"сгенерировано {output_tokens} токенов за {duration:.2f} секунд"
                )
                logger.info(f"ответ: {answer[:100]}...")

                log_llm_interaction(text, answer, duration)

                logger.info("отправка ответа в очередь")
                self.response_queue.put(answer)

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                logger.error(f"ошибка обработки запроса: {error_msg}", exc_info=True)

                response = self.config["error_message"]
                log_llm_interaction(prompt, response, duration, error_msg)
                self.response_queue.put(f"FALLBACK: {response}")

    def start(self):
        """
        запуск воркера в отдельном процессе
        """
        if self.process is None:
            logger.info("запуск процесса воркера LLM...")
            self.process = multiprocessing.Process(target=self.process_requests)
            self.process.start()
            logger.info("процесс воркера LLM запущен")

    def stop(self):
        """
        остановка воркера
        """
        if self.process is not None:
            logger.info("остановка воркера LLM...")
            self.request_queue.put("STOP")
            self.process.join(timeout=5)
            if self.process.is_alive():
                logger.warning("принудительная остановка процесса воркера LLM")
                self.process.terminate()
                self.process.join(timeout=5)
            logger.info("воркер LLM остановлен")
            self.process = None

    async def generate_response(self, prompt):
        """
        асинхронная генерация ответа на запрос

        Args:
            prompt: запрос пользователя или сообщения для модели

        Returns:
            str: ответ модели или сообщение об ошибке
        """

        if self.process is None or not self.process.is_alive():
            logger.warning("воркер LLM не запущен!запускаю...")
            self.start()

        start_time = time.time()
        logger.info("отправка запроса в очередь запросов")
        self.request_queue.put(prompt)

        timeout = self.config["timeout_seconds"]

        while True:
            try:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    error_msg = (
                        f"генерация ответа превысила таймаут после {elapsed:.2f} секунд"
                    )
                    logger.warning(error_msg)
                    log_llm_interaction(
                        prompt, self.config["timeout_message"], elapsed, error_msg
                    )
                    return self.config["timeout_message"]

                if not self.response_queue.empty():
                    response = self.response_queue.get_nowait()
                    logger.info("получен ответ из очереди")

                    if response.startswith("FALLBACK:"):
                        logger.warning("получен запасной ответ")
                        return response[9:]

                    logger.info("возвращаем обычный ответ")
                    return response

                await asyncio.sleep(0.1)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"ошибка получения ответа: {error_msg}", exc_info=True)
                log_llm_interaction(
                    prompt,
                    self.config["error_message"],
                    time.time() - start_time,
                    error_msg,
                )
                return self.config["error_message"]


llm_worker = LLMWorker()
