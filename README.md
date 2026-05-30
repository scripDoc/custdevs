# Кастдевы для AI-автоматизации

Локальная система для проведения и обработки кастдев-интервью.
Workflow: аудио → расшифровка (faster-whisper local) → структурированный разбор (Claude) → персональная упаковка для клиента.

## Быстрый старт

### 1. Установка (один раз)

```bash
# 1.1. Клонируем/распаковываем папку, переходим в неё
cd ~/custdevs

# 1.2. Делаем скрипты исполняемыми
chmod +x scripts/transcribe.py
chmod +x scripts/new_client.sh

# 1.3. Проверяем faster-whisper (уже стоит для voice-input)
python3 -c "from faster_whisper import WhisperModel; print('OK')"

# 1.4. Проверяем ffmpeg (нужен для видео)
ffmpeg -version | head -1
# Если нет: sudo pacman -S ffmpeg

# 1.5. Прогрев модели large-v3 (скачается один раз ~3GB)
# Лучше сделать вручную, чтобы при первом реальном кастдеве не ждать
python3 -c "
from faster_whisper import WhisperModel
print('Качаю large-v3...')
WhisperModel('large-v3', device='cuda', compute_type='float16')
print('OK, модель закеширована в ~/.cache/huggingface/')
"
```

### 2. Workflow по клиенту

```bash
# 2.1. Создаём папку клиента
./scripts/new_client.sh vladimir

# 2.2. Заполняем meta.md
# (контекст про человека, как говорит, что важно)
nvim clients/vladimir/meta.md

# 2.3. Кладём исходник (webm с Телемоста / mp4 с Zoom / m4a-бэкап) в 00_raw/
cp ~/Downloads/call_with_vladimir.webm clients/vladimir/00_raw/

# 2.4. Обрезаем нужный кусок и извлекаем аудио в 01_audio/
#      (через скилл trim_video или вручную:)
ffmpeg -ss 00:01:30 -to 00:45:00 -i clients/vladimir/00_raw/call_with_vladimir.webm \
    -vn -c:a aac -b:a 192k clients/vladimir/01_audio/call_with_vladimir.m4a

# 2.5. Транскрибируем (на GTX 1650 SUPER ~10-15 мин на час)
python3 scripts/transcribe.py \
    clients/vladimir/01_audio/call_with_vladimir.m4a \
    -o clients/vladimir/02_transcript/

# 2.6. Открываем шаблон промпта, копируем, добавляем расшифровку и meta.md,
#      отдаём в Claude (claude.ai project или Claude Code)
cat templates/structure_prompt.md
# Результат сохраняем в clients/vladimir/03_structure.md

# 2.7. Аналогично — упаковка
cat templates/package_prompt.md
# Результат в clients/vladimir/04_package.md — это и есть текст для отправки
```

## Гибридный режим

Локально на машине:
- Подготовка аудио (обрезка, enhance) — `ffmpeg`
- Хранение всех материалов
- Скрипты и шаблоны

В облаке:
- Транскрибация + диаризация — Deepgram API (аудио уходит в облако Deepgram)
- Разборы и упаковка — Claude

> **Приватность.** С переходом на Deepgram аудио кастдева отправляется в облако (раньше транскрибация была локальной). Это меняет модель приватности клиентских данных — учитывать при работе с чувствительными записями. Deepgram по умолчанию не использует данные для обучения моделей, но запись покидает машину.

В Claude Project на claude.ai:
- Создать проект "Кастдевы AI-услуги"
- В Knowledge загрузить: `CLAUDE.md`, `shared/custdev_protocol.md`, `templates/*`
- На каждого клиента — отдельный чат
- В чат подгружать `meta.md` + `transcript.md` + промпт из `templates/`

Преимущество: история по клиентам, поиск, можно вернуться через месяц.

## Полезные команды

```bash
# Транскрибация через Deepgram (nova-3 + диаризация v2, ключ из .env)
python3 -u scripts/transcribe.py file.m4a -o ./out/

# Без разделения спикеров (монолог, один голос)
python3 -u scripts/transcribe.py file.m4a -o ./out/ --no-diarize

# Зафиксировать язык явно (по умолчанию multi = multilingual)
python3 -u scripts/transcribe.py file.m4a -o ./out/ --language ru
```

## Структура папок

Описана в `CLAUDE.md`. Кратко по клиенту:
- `00_raw/` — исходники (webm с Телемоста, m4a-бэкапы с iPhone, любое сырьё). Не удаляются после обрезки — нужны для повторных прогонов.
- `01_audio/` — готовый `.m4a` после обрезки, вход для `transcribe.py`.
- `02_transcript/` — результат `transcribe.py`.
- `03_structure.md` / `04_package.md` — разбор и упаковка для клиента.

## Доработки в будущем

- [ ] Скрипт для автоматического запроса structure → package (через Anthropic API)
- [ ] Дашборд статусов по клиентам
- [ ] Авто-публикация в Obsidian / Notion
- [ ] Шаблоны промптов под разные ниши (мебельщики / кондитеры / терапевты)
