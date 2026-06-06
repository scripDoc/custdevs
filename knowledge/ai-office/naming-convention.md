# AI-Office — конвенция имён артефактов

Источник истины по тому, какой агент что пишет, кто это читает и где оно лежит. Файловый handoff — основа офиса: на входе каждой стадии лежит ровно тот файл, который произвёл предыдущий агент.

## Поток артефактов

```
транскрипт (02_transcript/<slug>.transcript.md)
   │
   ▼ client-strategist
strategist_brief.md
   │
   ▼ product-architect
product_spec_brief.md  +  product_plan.md
   │                          └────────────► (Алик: проверка реализуемости)
   ▼ pricing-strategist (читает product_plan.md + strategist_brief.md)
pricing_offer_brief.md  +  pricing_strategy.md
   │                          └────────────► (Алик: подтверждает цену → в разговор)
   ▼ dr-copywriter (читает strategist_brief.md + product_spec_brief.md + pricing_offer_brief.md)
copywriter_draft.md
   │
   ▼ landing-designer
design_spec.md
   │
   ▼ frontend-dev (читает design_spec.md + copywriter_draft.md)
deliverables/<slug>/  (index.html + styles.css + ...)
   │
   ├─▼ Директор: scripts/render_screenshot.py deliverables/<slug>/ → /tmp/shots/<slug>.png
   │     ▼ sales-evaluator (визуальный режим: критерии 9–12, /40) — ИНФОРМАТИВНО, эскалация Алику с PNG
   │
   ▼ (Алик / deploy_landing — отдельный человеческий шаг)
live URL
```

Сквозные файлы: `_agent_notes.md` (пишут все агенты, читают Алик/Директор) и `_director_report.md` (пишет Директор).

**Два гейта перед человеком** (проверяют готовые артефакты, оси ортогональны): `qa-controller` (честность: фабрикация / slop / соответствие → `_qa_report.md`) и `sales-evaluator` (продающая сила — в ДВУХ проходах: **текст** по копи, критерии 1–8 /80, до дизайна; **визуал** по рендеру собранного лендинга, критерии 9–12 /40, после фронта — рендер через `scripts/render_screenshot.py`, информативно, эскалация Алику с PNG). **Порядок: `qa-controller` ПЕРВЫЙ, до `sales-evaluator`** — нет смысла мерить продающую силу того, что может врать; только QA-PASS пропускает артефакт к оценке продажи и к человеку. На BLOCK → фикс производящим агентом → **re-check qa-controller** (подтверждает переход BLOCK→PASS) → дальше. qa-controller — единственный, кроме стратега, кто **читает транскрипт** (как верификатор, чтобы сверить грунтовку фактов).

## Артефакты

| Файл | Кто пишет | Кто читает | Где лежит | Назначение |
|------|-----------|------------|-----------|------------|
| `strategist_brief.md` | client-strategist | architect, copywriter | `clients/<slug>/` | Портрет клиента: аватар, awareness, оффер, механизм, VoC, стоп-лист, слабые сигналы |
| `product_spec_brief.md` | product-architect | dr-copywriter | `clients/<slug>/` | Рамка реального для копи: что обещать, цифры, чего НЕ обещать (без техники) |
| `product_plan.md` | product-architect | Алик | `clients/<slug>/` | План реализации: стек, сложность, этапы, открытые вопросы |
| `pricing_offer_brief.md` | pricing-strategist | dr-copywriter | `clients/<slug>/` | Оффер-рамка для копи: формат CTA/следующего шага, цена на лендинг да/нет (по умолчанию нет), чего не говорить. Без внутренней экономики |
| `pricing_strategy.md` | pricing-strategist | Алик | `clients/<slug>/` | Ценовая стратегия: сегмент, триангуляция рынка, ставка часа, себестоимость (два пола), вилка, структура (фикс-абонентка), скидка за кейс, переговоры |
| `copywriter_draft.md` | dr-copywriter | landing-designer, frontend-dev | `clients/<slug>/` | Продающий текст по секциям + логика + stop-slop score |
| `design_spec.md` | landing-designer | frontend-dev | `clients/<slug>/` | Дизайн-спека: концепция, типографика, цвет, секции, движение, Cialdini |
| `deliverables/<slug>/` | frontend-dev | frontend-dev → `deploy_landing` (сам), Алик | `deliverables/<slug>/` | Готовый статический лендинг (index.html + ассеты); фронтендер деплоит сам → live URL |
| `/tmp/shots/<slug>.png` | Директор (`scripts/render_screenshot.py`) | sales-evaluator (визуал), Алик | `/tmp/shots/` (НЕ коммитится) | Честный fullPage-рендер собранного лендинга для визуального прохода (playwright + reduced-motion + скролл). Эфемерный, в git не идёт |
| `_agent_notes.md` | все агенты (опц.) | Алик (Этап 1) / Директор (Этап 2) | `clients/<slug>/` | Голос сотрудника: замечания/предложения/эскалации между агентами |
| `_qa_report.md` | qa-controller | Директор / Алик | `clients/<slug>/` | Гейт честности: вердикт PASS/BLOCK + находки (фабрикация / slop / соответствие) с опорой на транскрипт/бриф + предложения фикса |
| `_director_report.md` | director | Алик | `clients/<slug>/` | Диагностика прогона: стадии, заметки, гейты, эскалации, проседания |
| `_run_logs/run_<id>_<date>.log` | director (+ агенты) | Алик / диагностика | `clients/<slug>/_run_logs/` | Сырой лог прогона: действия с timestamp + RUN ID. Ведётся всегда, для сравнения прогонов |
| `_runs_registry.md` | director | director (пикер) / Алик | `knowledge/ai-office/` | Реестр прогонов лендинг-пайплайна (клиент → RUN ID → дата → вердикт qa → превью URL → эскалации). Источник пометок «уже прогнан» для пикера Директора. Дописывается в конец. |
| `_sites_registry.md` | director / Алик | director (пикер) / Алик | `knowledge/ai-office/` | Реестр задеплоенных лендингов (проект Vercel, URL, статус sent/frozen/current/honest/live). Отдельно от прогонов. |

> **Директор — РОЛЬ/СКИЛЛ** (`.claude/skills/director/SKILL.md`), исполняется в основной сессии, НЕ Task-субагент (иначе стадии — второй уровень вложенности). Один клиент за прогон; изоляция = терминал на клиента. Гейты перед человеком: **qa-controller первый**, затем sales-evaluator. Прод-деплой на паузе (только превью).

## Правила

- **Имена точные.** Подчёркивания и регистр как в таблице. `design_spec.md` (не `design-spec`), `product_spec_brief.md`, `product_plan.md`.
- **Один артефакт — один файл.** Перегенерация — поверх (с осторожностью), не плодить `_v2`.
- **Локация — `clients/<slug>/`** для всех брифов/спек/заметок. Исключение: собранный код в `deliverables/<slug>/`.
- **Сквозные файлы — append-safe.** `_agent_notes.md` общий: дописывать свой блок в конец (Read→Write или Edit), не затирать чужое. Формат блока: `## <Роль> → <КОМУ> · <дата>` + текст + `Важность:`.
- **`_director_report.md`** ведёт только Директор; обновляет/дописывает по ходу прогона.
- **Транскрипт** (`02_transcript/<slug>.transcript.md`) — единственный первоисточник, читает только стратег. Производные/интерпретации поверх транскрипта офис НЕ использует (старый PDF-пайплайн с такими файлами выведен из эксплуатации → `_archive/old_pdf_pipeline/`).
- **Копирайтер теперь читает ДВА брифа:** `product_spec_brief.md` (что продаём — рамка реального) + `pricing_offer_brief.md` (цена/формат/следующий шаг). **По вопросам цены, формата и CTA главнее `pricing_offer_brief.md`** — там финальное решение по offer/цене/формату созвона. По продукту/обещаниям — `product_spec_brief.md`. Если `pricing_offer_brief.md` нет (ранний прогон до ценового агента) — копирайтер не выдумывает цену/формат, ставит `[нужен факт: цена/формат]`.
