---
name: generate_pdf
description: Собирает финальный PDF клиента из 04_package.md по шаблону templates/package_template.html через WeasyPrint (Python API), проверяет вёрстку (число страниц, пустые страницы, сироты). Запускается после готового пакета, последний шаг конвейера. Триггеры — «сделай pdf для <клиент>», «сгенерируй пакет в pdf», «финальный документ для <клиент>», «собери pdf».
---

# generate_pdf

## Перед выполнением

Прочитай `failures.md` (grep по тегам `#pdf`, `#weasyprint`, `#wkhtmltopdf`, `#layout`, `#html`). Если есть релевантные записи — учти в плане. Не пересказывай grep пользователю, это фоновая проверка.

```bash
grep -A 5 "#pdf\|#weasyprint\|#wkhtmltopdf\|#layout\|#html" failures.md
```

## Идеология

Скилл — последний шаг конвейера. На входе — готовый `clients/<slug>/04_package.md` (markdown-пакет, собранный по `templates/package_prompt.md`). На выходе — `clients/<slug>/05_final.pdf` для отправки клиенту.

**Что скилл делает руками** (не пытайся всё свалить в один shell-скрипт):
1. Читает markdown пакета.
2. Парсит секции по якорным заголовкам из `package_prompt.md`.
3. Подставляет содержимое в HTML-шаблон.
4. Рендерит PDF через `weasyprint.HTML(...).write_pdf(...)`.
5. Проверяет вёрстку (число страниц, пустые / сиротские страницы) — если криво, **одна попытка** пересборки с корректировкой разрывов.
6. Делает PNG превью первой страницы для визуальной проверки.

**Что скилл НЕ делает:** не редактирует исходный текст пакета. Если контент кривой — это вопрос к `package_prompt.md`, не к рендеру.

## Триггеры

- «сделай pdf для <клиент>», «собери pdf для <клиент>»
- «сгенерируй пакет в pdf», «финальный документ для <клиент>»
- «упакуй в pdf»
- Авто-вызов из `kickoff` (шаг 8 конвейера)

## Зависимости

WeasyPrint (Python) + системные библиотеки рендера (pango, cairo, gdk-pixbuf2). На Manjaro/Arch ставится так:

```bash
pip install --user --break-system-packages weasyprint markdown pypdfium2
sudo pacman -S pango cairo gdk-pixbuf2
```

**Почему не wkhtmltopdf.** Upstream-проект `wkhtmltopdf` архивирован в апреле 2023, пакет удалён из официальных репозиториев Manjaro/Arch. Доступен только через AUR (`wkhtmltopdf-static`) без поддержки. WeasyPrint — современная активная замена с лучшей поддержкой CSS и Unicode. См. запись в `failures.md` с тегами `#weasyprint #wkhtmltopdf #manjaro`.

Перед первым запуском проверить:

```bash
python3 -c "import weasyprint; print(weasyprint.__version__)" 2>&1
python3 -c "import markdown" 2>&1 | grep -q ModuleNotFoundError && echo "MISSING: markdown"
python3 -c "import pypdfium2" 2>&1 | grep -q ModuleNotFoundError && echo "MISSING: pypdfium2"
pacman -Q pango cairo gdk-pixbuf2 2>&1 | grep -q "не найден\|was not found" && echo "MISSING: pango/cairo/gdk-pixbuf2"
```

Если чего-то нет — сказать пользователю одной строкой:

> Для PDF-рендера нужны: python-пакеты `weasyprint`, `markdown`, `pypdfium2` (`pip install --user --break-system-packages weasyprint markdown pypdfium2`) и системные библиотеки `pango cairo gdk-pixbuf2` (`sudo pacman -S pango cairo gdk-pixbuf2`). Поставь и зови снова.

Не пытаться поставить молча.

## Контракт на вход

`clients/<slug>/04_package.md` собран по `templates/package_prompt.md` с заголовками:

- `# Разбор` — h1 (TITLE)
- Первая строка после h1 — обращение (GREETING)
- Параграф(ы) до первой `## Где ты сейчас` — лид (INTRO)
- `## Где ты сейчас` → SECTION_HERE_NOW
- `## Куда хочешь дойти` → SECTION_GOAL
- `## Связки` → SECTION_CONNECTIONS (внутри `**Связка N.**` блоки)
- `## И ещё одна вещь — про режим работы` (или вариация) → SECTION_REGIME (может содержать `> ...` callout)
- `## Колесо` → SECTION_WHEEL (внутри `### Шестерёнка N.` блоки + финальный `> **Что важно:** ...`)
- `## Если решишь двигаться` → SECTION_NEXT
- `## Что ещё стоит уточнить` → SECTION_OPEN
- Финальный блок `---` + два параграфа курсивом → CLOSING

Если структура не такая — стоп, сообщить какой раздел не найден, не пытаться угадать.

## Парсинг и рендер

Используй inline-Python (через `python3 -c '...'` или временный файл `/tmp/render_pdf_<slug>.py`). Логика:

```python
import re, sys, datetime
from pathlib import Path
import markdown as md

slug = "<slug>"  # подставляется из контекста
date = "<YYYY-MM-DD>"  # дата кастдева из meta.md (или сегодняшняя если не нашли)
client_root = Path(f"clients/{slug}")
src = (client_root / "04_package.md").read_text(encoding="utf-8")
tpl = Path("templates/package_template.html").read_text(encoding="utf-8")

def split_sections(text):
    """Возвращает dict с ключами: title, greeting, intro, here_now, goal,
    connections, regime, wheel, next, open, closing."""
    # h1
    m = re.search(r"^#\s+(.+?)$", text, re.M)
    title = m.group(1).strip() if m else "Разбор"

    # всё после h1 — тело
    body = text[m.end():] if m else text

    # секции — по h2
    parts = re.split(r"(?m)^##\s+(.+?)$", body)
    # parts[0] = всё до первой h2 (greeting + intro)
    # parts[1::2] = заголовки h2
    # parts[2::2] = тела секций

    head = parts[0].strip()
    head_lines = [l for l in head.split("\n\n") if l.strip()]
    greeting = head_lines[0] if head_lines else ""
    intro_md = "\n\n".join(head_lines[1:]) if len(head_lines) > 1 else ""

    sections = {}
    for i in range(1, len(parts), 2):
        sections[parts[i].strip()] = parts[i+1].strip()

    # Закрытие — последний блок после "---" в любой секции
    # обычно в "Что ещё стоит уточнить"
    closing_md = ""
    for k, v in sections.items():
        m = re.search(r"\n---\s*\n(.+)$", v, re.S)
        if m:
            closing_md = m.group(1).strip()
            sections[k] = v[:m.start()].strip()

    return title, greeting, intro_md, sections, closing_md

title, greeting, intro_md, sections, closing_md = split_sections(src)

def render_md(s):
    return md.markdown(s or "", extensions=["extra", "sane_lists"])

# Связки → div.link-block
def render_connections(s):
    blocks = re.split(r"(?m)^\*\*Связка\s+\d+\.\*\*\s*", s)
    blocks = [b.strip() for b in blocks if b.strip()]
    out = []
    for i, b in enumerate(blocks, 1):
        # Первая строка — заголовок связки до →
        head, _, rest = b.partition("\n")
        head_html = head.replace("→", '<span class="link-arrow">→</span>')
        out.append(
            f'<div class="link-block">'
            f'<div class="link-title">Связка {i}. {head_html}</div>'
            f'{render_md(rest.strip())}'
            f'</div>'
        )
    return "\n".join(out)

# Шестерёнки → div.gear со стрелками между ними
def render_wheel(s):
    # отделить финальный "> **Что важно:** ..." callout
    important_html = ""
    m = re.search(r"\n>\s+\*\*Что важно:\*\*(.+)$", s, re.S)
    if m:
        important_html = (
            f'<div class="callout-info"><strong>Что важно:</strong>'
            f'{render_md(m.group(1).strip())}</div>'
        )
        s = s[:m.start()].strip()

    # лид (текст до первой ### Шестерёнка)
    lead, sep, rest = s.partition("### Шестерёнка")
    lead_html = render_md(lead.strip())
    if sep:
        rest = "### Шестерёнка" + rest

    gears = re.split(r"(?m)^###\s+Шестерёнка\s+(\d+)\.\s*(.+?)$", rest)
    # gears[0] = пусто, далее тройками: num, title, body
    out = [lead_html]
    for i in range(1, len(gears), 3):
        num, gname, body = gears[i], gears[i+1], gears[i+2]
        # выкинуть из body одиночные строки "→"
        body_clean = re.sub(r"(?m)^\s*→\s*$", "", body).strip()
        out.append(
            f'<div class="gear">'
            f'<div class="gear-title"><span class="gear-num">{num}.</span>{gname.strip()}</div>'
            f'{render_md(body_clean)}'
            f'</div>'
        )
        if i + 3 < len(gears):
            out.append('<div class="gear-arrow">↓</div>')
    if important_html:
        out.append(important_html)
    return "\n".join(out)

# Режим работы — обычный markdown + блок "> **Поэтому первый шаг должен..."
def render_regime(s):
    # callout-step выделяем отдельно
    m = re.search(r"\n>\s+\*\*Поэтому первый шаг(.+?)\*\*", s, re.S)
    if m:
        callout = (
            f'<div class="callout-step"><strong>Поэтому первый шаг'
            f'{m.group(1)}</strong></div>'
        )
        return render_md(s[:m.start()].strip()) + callout
    return render_md(s)

# Закрытие — два параграфа курсивом
def render_closing(s):
    paragraphs = [p.strip() for p in s.split("\n\n") if p.strip()]
    out = []
    for p in paragraphs:
        # снять обрамляющий *
        text = p.strip("*").strip()
        out.append(f"<p>{text}</p>")
    return "\n".join(out)

filled = (tpl
    .replace("{{TITLE}}", title)
    .replace("{{DATE}}", date)
    .replace("{{GREETING}}", greeting)
    .replace("{{INTRO}}", render_md(intro_md))
    .replace("{{SECTION_HERE_NOW}}", render_md(sections.get("Где ты сейчас", "")))
    .replace("{{SECTION_GOAL}}", render_md(sections.get("Куда хочешь дойти", "")))
    .replace("{{SECTION_CONNECTIONS}}", render_connections(sections.get("Связки", "")))
    .replace("{{SECTION_REGIME}}", render_regime(
        sections.get("И ещё одна вещь — про режим работы",
        next((v for k, v in sections.items() if "режим" in k.lower()), ""))))
    .replace("{{SECTION_WHEEL}}", render_wheel(sections.get("Колесо", "")))
    .replace("{{SECTION_NEXT}}", render_md(sections.get("Если решишь двигаться", "")))
    .replace("{{SECTION_OPEN}}", render_md(sections.get("Что ещё стоит уточнить", "")))
    .replace("{{CLOSING}}", render_closing(closing_md))
)

out_html = client_root / "_temp_package.html"
out_html.write_text(filled, encoding="utf-8")
print(out_html)
```

## Команда рендера (WeasyPrint)

Рендер делается прямо в том же Python-скрипте, без отдельного shell-вызова. Поля и формат страницы управляются `@page` в CSS — снаружи ничего передавать не нужно:

```python
from weasyprint import HTML

out_pdf = client_root / "05_final.pdf"
HTML(filename=str(out_html), base_url=str(client_root)).write_pdf(
    str(out_pdf),
    # стили внутри HTML, дополнительных stylesheets не передаём
)
print(out_pdf)
```

**Почему `base_url=client_root`** — на случай, если в шаблоне когда-то появятся локальные ассеты (логотип, иконки): WeasyPrint резолвит их относительно `base_url`. Сейчас не нужно, но не мешает.

**Stderr WeasyPrint** часто содержит warning-и про шрифты («cannot load font ...»). Это не ошибка — fallback на `sans-serif` отрабатывает корректно. Игнорировать, если PDF собрался.

## Постпроверка вёрстки

После рендера:

```python
import pypdfium2 as pdfium
pdf = pdfium.PdfDocument("clients/<slug>/05_final.pdf")
n_pages = len(pdf)

# 1. число страниц — норма 4–6
norm = 4 <= n_pages <= 6

# 2. почти пустая первая страница — баг с разрывами
page1_text = pdf[0].get_textpage().get_text_range().strip()
page1_too_empty = len(page1_text) < 250

# 3. последняя страница — только закрытие на 1–2 строки
last_text = pdf[n_pages - 1].get_textpage().get_text_range().strip()
last_orphan = len(last_text) < 200 and "Спасибо за разговор" in last_text

# 4. превью первой страницы → PNG
pdf[0].render(scale=2).to_pil().save(f"clients/<slug>/05_final.preview.png")
```

**Если problem обнаружен** — одна попытка пересобрать:
- `page1_too_empty` → убрать из шаблона `class="section-break"` для первой секции после h1.
- `last_orphan` → добавить `page-break-before: avoid` для блока закрытия (через инлайн-style на `.closing`).

После одной попытки — если всё ещё криво, отчитаться пользователю с указанием конкретной проблемы и **записать в `failures.md`** с тегами `#pdf #weasyprint #layout`.

## Очистка артефактов

После успеха `_temp_package.html` оставить (для дебага следующего запуска), `05_final.preview.png` оставить (превью).

## Отчёт пользователю

```
✅ PDF собран: clients/<slug>/05_final.pdf
   Страниц: <N>  (норма 4–6)
   Размер: <KB>
   Превью первой страницы: clients/<slug>/05_final.preview.png

Проверь визуально превью — если ок, можно отправлять клиенту
(шаблон сопроводительного: clients/_template/SEND_TEMPLATE.md).
```

Если получилось не идеально — упомянуть честно:

```
⚠️ PDF собран, но <N> страниц вместо нормы 4–6 / на стр.1 много пустого / последняя страница — сирота.
   Файл: clients/<slug>/05_final.pdf
   Что попробовать: посмотреть стр. <N> в превью, при необходимости подправить вручную в 04_package.md и пересобрать.
   Записал в failures.md (теги: #pdf #weasyprint #layout).
```

## После провала

Если PDF получился криво и автоматическая корректировка не помогла — в `failures.md` запись:

```
## YYYY-MM-DD — generate_pdf ⚠️/⛔
**Тег:** #pdf #weasyprint #layout
**Что сломалось:** <конкретно: «1-я страница пустая», «шестерёнка 3 разрезана пополам», «последняя страница — только закрытие на 2 строки»>
**Что помогло / не помогло:** ...
**Идея для шаблона:** <если есть>
```

## Теги в failures.md

`#pdf #generate #weasyprint #layout #html`
