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
   ▼ dr-copywriter (читает strategist_brief.md + product_spec_brief.md)
copywriter_draft.md
   │
   ▼ landing-designer
design_spec.md
   │
   ▼ frontend-dev (читает design_spec.md + copywriter_draft.md)
deliverables/<slug>/  (index.html + styles.css + ...)
   │
   ▼ (Алик / deploy_landing — отдельный человеческий шаг)
live URL
```

Сквозные файлы: `_agent_notes.md` (пишут все агенты, читают Алик/Директор) и `_director_report.md` (пишет Директор).

## Артефакты

| Файл | Кто пишет | Кто читает | Где лежит | Назначение |
|------|-----------|------------|-----------|------------|
| `strategist_brief.md` | client-strategist | architect, copywriter | `clients/<slug>/` | Портрет клиента: аватар, awareness, оффер, механизм, VoC, стоп-лист, слабые сигналы |
| `product_spec_brief.md` | product-architect | dr-copywriter | `clients/<slug>/` | Рамка реального для копи: что обещать, цифры, чего НЕ обещать (без техники) |
| `product_plan.md` | product-architect | Алик | `clients/<slug>/` | План реализации: стек, сложность, этапы, открытые вопросы |
| `copywriter_draft.md` | dr-copywriter | landing-designer, frontend-dev | `clients/<slug>/` | Продающий текст по секциям + логика + stop-slop score |
| `design_spec.md` | landing-designer | frontend-dev | `clients/<slug>/` | Дизайн-спека: концепция, типографика, цвет, секции, движение, Cialdini |
| `deliverables/<slug>/` | frontend-dev | Алик / deploy_landing | `deliverables/<slug>/` | Готовый статический лендинг (index.html + ассеты), к деплою |
| `_agent_notes.md` | все агенты (опц.) | Алик (Этап 1) / Директор (Этап 2) | `clients/<slug>/` | Голос сотрудника: замечания/предложения/эскалации между агентами |
| `_director_report.md` | director | Алик | `clients/<slug>/` | Диагностика прогона: стадии, заметки, гейты, эскалации, проседания |

## Правила

- **Имена точные.** Подчёркивания и регистр как в таблице. `design_spec.md` (не `design-spec`), `product_spec_brief.md`, `product_plan.md`.
- **Один артефакт — один файл.** Перегенерация — поверх (с осторожностью), не плодить `_v2`.
- **Локация — `clients/<slug>/`** для всех брифов/спек/заметок. Исключение: собранный код в `deliverables/<slug>/`.
- **Сквозные файлы — append-safe.** `_agent_notes.md` общий: дописывать свой блок в конец (Read→Write или Edit), не затирать чужое. Формат блока: `## <Роль> → <КОМУ> · <дата>` + текст + `Важность:`.
- **`_director_report.md`** ведёт только Директор; обновляет/дописывает по ходу прогона.
- **Транскрипт** (`02_transcript/<slug>.transcript.md`) — единственный первоисточник, читает только стратег. Производные старого PDF-пайплайна (`meta.md`, `03_structure.md`, `04_package.md`) офис НЕ использует.
