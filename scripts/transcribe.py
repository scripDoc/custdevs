#!/usr/bin/env python3
"""
transcribe.py — расшифровка аудио через Deepgram Nova-3 + диаризация.

Заменил локальный faster-whisper (см. failures.md, 2026-05-28). Зачем:
- диаризация (разделение спикеров) — Deepgram отдаёт «кто говорит» из коробки;
- скорость облака (час аудио обрабатывается за минуты, а не за час на CPU);
- не трогает локальные ресурсы (voice-input daemon / GPU остаются свободными).

Использование:
    python3 transcribe.py path/to/audio.m4a
    python3 transcribe.py call.m4a -o ./output_dir
    python3 transcribe.py call.m4a --no-diarize        # без разделения спикеров
    python3 transcribe.py call.m4a --language ru        # язык вместо multi

Три файла рядом со входным (или в --output):
    <name>.transcript.md    — markdown: **[HH:MM:SS–HH:MM:SS]** [Спикер N] текст
    <name>.transcript.txt   — плоский текст без разметки
    <name>.transcript.json  — нормализованные сегменты + полный ответ Deepgram

Ключ берётся из переменной окружения DEEPGRAM_API_KEY либо из файла .env в
корне проекта (custdevs/.env). Получить ключ: https://console.deepgram.com/

Зависимости:
    pip install --user --break-system-packages 'deepgram-sdk>=3.7,<4'
    ВАЖНО: пинить <4 — v4+ переписан под Fern и несовместим с вызовом
    client.listen.rest.v("1").transcribe_file(...), который тут используется.
"""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

try:
    import httpx
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        PrerecordedOptions,
    )
except ImportError:
    print("❌ deepgram-sdk не установлен. Поставь: "
          "pip install --user --break-system-packages 'deepgram-sdk>=3.7,<4'")
    sys.exit(1)


# Дефолты — те же, что проверены на проекте mentor-bot (виртуальный эксперт).
DEFAULT_MODEL = "nova-3"
DEFAULT_LANGUAGE = "multi"          # multilingual, включая русский
DEFAULT_DIARIZE_VERSION = "v2"      # Diarize v2 авто-детектит число спикеров
DEFAULT_TIMEOUT_SEC = 600           # один запрос на длинном файле (1–2 часа)


def format_timestamp(seconds: float) -> str:
    """Конвертирует секунды в HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _load_api_key() -> str | None:
    """Ключ Deepgram: сначала из окружения, потом из .env в корне проекта."""
    key = os.environ.get("DEEPGRAM_API_KEY")
    if key and key.strip():
        return key.strip()

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        name, sep, value = line.partition("=")
        if not sep or name.strip() != "DEEPGRAM_API_KEY":
            continue
        value = value.strip()
        if " #" in value:                       # отрезать inline-комментарий
            value = value.split(" #", 1)[0].strip()
        value = value.strip('"').strip("'")
        if value:
            return value
    return None


def _normalize_segments(raw: dict) -> list[dict]:
    """Deepgram-ответ → список сегментов {start, end, text, speaker}.

    Источник — results.utterances (флаг utterances=True): каждая utterance
    уже одного спикера и одного непрерывного промежутка. Спикеры Deepgram —
    целые 0,1,2…; сохраняем как есть (рендерятся как «[Спикер N]»).
    """
    utterances = (raw.get("results") or {}).get("utterances") or []
    segments: list[dict] = []
    for u in utterances:
        text = (u.get("transcript") or "").strip()
        if not text:
            continue
        speaker = u.get("speaker")
        segments.append({
            "start": float(u.get("start", 0.0)),
            "end": float(u.get("end", 0.0)),
            "text": text,
            "speaker": int(speaker) if speaker is not None else 0,
        })
    if segments:
        return segments

    # Фоллбэк: utterances пустые — берём общий транскрипт одним блоком.
    channels = (raw.get("results") or {}).get("channels") or []
    if channels:
        alts = channels[0].get("alternatives") or []
        if alts:
            text = (alts[0].get("transcript") or "").strip()
            if text:
                dur = (raw.get("metadata") or {}).get("duration", 0.0)
                segments.append({"start": 0.0, "end": float(dur), "text": text, "speaker": 0})
    return segments


def _heartbeat(stop_event: threading.Event, started: float):
    """Печатает живой статус, пока Deepgram обрабатывает запрос."""
    while not stop_event.wait(10):
        print(f"  ⏳ Deepgram обрабатывает... {time.time() - started:.0f}с", flush=True)


def transcribe(
    input_path: Path,
    output_dir: Path,
    language: str = DEFAULT_LANGUAGE,
    model: str = DEFAULT_MODEL,
    diarize: bool = True,
    diarize_version: str = DEFAULT_DIARIZE_VERSION,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
):
    """Прогон одного файла через Deepgram pre-recorded API."""

    api_key = _load_api_key()
    if not api_key:
        print("❌ DEEPGRAM_API_KEY не задан. Заполни custdevs/.env "
              "(см. .env.example) или экспортируй переменную окружения.")
        sys.exit(1)

    base_name = input_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{base_name}.transcript.md"
    txt_path = output_dir / f"{base_name}.transcript.txt"
    json_path = output_dir / f"{base_name}.transcript.json"

    size_mb = input_path.stat().st_size / 1e6
    print(f"📂 Файл: {input_path} ({size_mb:.1f} МБ)")
    print(f"☁️  Провайдер: Deepgram ({model}, язык={language}, "
          f"диаризация={'v' + diarize_version[1:] if diarize else 'выкл'})")
    print(f"⬆️  Загрузка и обработка (timeout {timeout_sec}с)...", flush=True)

    client = DeepgramClient(api_key, DeepgramClientOptions(options={"keepalive": "true"}))
    payload = {"buffer": input_path.read_bytes()}
    options = PrerecordedOptions(
        model=model,
        language=language,
        diarize=diarize,
        diarize_version=diarize_version if diarize else None,
        smart_format=True,
        paragraphs=True,
        utterances=True,
        punctuate=True,
    )

    started = time.time()
    stop_event = threading.Event()
    hb = threading.Thread(target=_heartbeat, args=(stop_event, started), daemon=True)
    hb.start()
    try:
        # SDK 3.x: REST listen endpoint, синхронный вызов.
        response = client.listen.rest.v("1").transcribe_file(
            payload,
            options,
            timeout=httpx.Timeout(timeout_sec, connect=30.0),
        )
    except Exception as e:
        stop_event.set()
        print(f"\n❌ Deepgram упал: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        stop_event.set()
    elapsed = time.time() - started

    # Нормализуем ответ в dict.
    if hasattr(response, "to_dict"):
        raw = response.to_dict()
    elif hasattr(response, "to_json"):
        raw = json.loads(response.to_json())
    elif isinstance(response, dict):
        raw = response
    else:
        print(f"❌ Неожиданный тип ответа Deepgram: {type(response).__name__}")
        sys.exit(1)

    segments = _normalize_segments(raw)
    duration = (raw.get("metadata") or {}).get("duration")
    duration = float(duration) if duration is not None else 0.0
    n_speakers = len({s["speaker"] for s in segments}) if diarize else 0

    if not segments:
        print("⚠️  Deepgram вернул пустой транскрипт — проверь запись/язык.")

    # ── Markdown (совместим со старым форматом: те же таймкоды, + спикер) ──
    md_lines = [f"# Расшифровка: {base_name}", ""]
    md_lines += [
        f"- **Длительность:** {format_timestamp(duration)}",
        f"- **Провайдер:** Deepgram ({model}, {language})",
        f"- **Диаризация:** {'v' + diarize_version[1:] + f', спикеров: {n_speakers}' if diarize else 'выключена'}",
        "",
        "---",
        "",
    ]
    for seg in segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        md_lines.append(f"**[{start}–{end}]** [Спикер {seg['speaker']}] {seg['text']}")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    txt_path.write_text(" ".join(seg["text"] for seg in segments), encoding="utf-8")
    json_path.write_text(
        json.dumps({
            "provider": "deepgram",
            "model": model,
            "language": language,
            "diarize": diarize,
            "diarize_version": diarize_version if diarize else None,
            "duration": duration,
            "n_speakers": n_speakers,
            "segments": segments,
            "raw": raw,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    speed = duration / elapsed if elapsed > 0 else 0
    print()
    print(f"✅ Готово за {elapsed:.0f}с "
          f"({format_timestamp(duration)} аудио, x{speed:.1f} к реальному времени)")
    if diarize:
        print(f"   Спикеров: {n_speakers}, сегментов: {len(segments)}")
    print(f"   Markdown:  {md_path}")
    print(f"   Чистый:    {txt_path}")
    print(f"   JSON:      {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Расшифровка аудио через Deepgram Nova-3 + диаризация")
    parser.add_argument("input", type=Path, help="Путь к аудио/видео файлу")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Папка для результата (по умолчанию рядом со входным)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Модель Deepgram (дефолт {DEFAULT_MODEL})")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE,
                        help=f"Язык (дефолт {DEFAULT_LANGUAGE} = multilingual, включая русский)")
    parser.add_argument("--no-diarize", dest="diarize", action="store_false",
                        help="Отключить разделение спикеров")
    parser.add_argument("--diarize-version", default=DEFAULT_DIARIZE_VERSION,
                        help=f"Версия диаризации Deepgram (дефолт {DEFAULT_DIARIZE_VERSION})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC,
                        help=f"Таймаут запроса в секундах (дефолт {DEFAULT_TIMEOUT_SEC})")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Файл не найден: {args.input}")
        sys.exit(1)

    output_dir = args.output if args.output else args.input.parent

    transcribe(
        input_path=args.input,
        output_dir=output_dir,
        language=args.language,
        model=args.model,
        diarize=args.diarize,
        diarize_version=args.diarize_version,
        timeout_sec=args.timeout,
    )


if __name__ == "__main__":
    main()
