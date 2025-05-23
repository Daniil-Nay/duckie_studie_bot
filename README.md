# 🦆 Duckie Studie bot

Бот создан для помощи студентам и школьникам в изучении математических дисциплин в рамках школы ММ'25, ИТМО.
## О проекте
Duckie Studie Bot — это обучающий Telegram-бот с двумя основными режимами:

- Режим обучения по темам — предоставляет теорию, схемы и медиа по математике

- Интерактивный режим — позволяет вести диалог с ботом на основе языковой модели



## Возможности
Интеграция с языковой моделью (LLM) через transformers и PyTorch

- ⭐ Интерактивное общение на естественном языке с LLM 

- ⭐ Отслеживание активности пользователя (таймеры бездействия)

- ⭐  Навигация по темам и подразделам

- ⭐  Поддержка изображений и видео

- ⭐  Встроенные механизмы AI Safety (фильтрация опасных запросов)

- ⭐  Гибкое управление состояниями (FSM)


##  Установка
Два варианта:
1) Создать среду CONDA/venv (Я предпочитаю с conda работать):

conda env create --n duckie_studie python==3.10

conda activate duckie_studie

pip install -r requirements.txt

3) скрипт для запуска run.py ⭐

В любом из случаев понадобятся:
tg bot token
## Структура проекта

├── bot.py                   # 'Сердце' бота: отвечает за рабочий цикл

├── config/                  # Загрузка конфигурации из .env

├── handlers/                # Хэндлеры: команды, колбэки, интерактив

├── keyboards/               # Генерация клавиатур

├── states/                  # Машина состояний (FSM)

├── llm/                     # Интеграция с языковой моделью

├── database/                # Работа с SQLite и структура тем

├── content/                 # Медиа-учебный материал

## Демонстрация (презенация + в ней есть демонстрационные ролики)

[Ссылка на google slides](https://docs.google.com/presentation/d/1Oo8gN-56uw-TlCNnI9r-S6np_SR63qfGM_8ttNff4WE/edit?usp=sharing)



