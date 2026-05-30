# AI-Office для лендингов — Backlog реализации

## Цель

Собрать sequential pipeline из 4 виртуальных AI-сотрудников внутри Claude Code, которые из брифа клиента и транскрипта кастдева производят production-grade лендинг с деплоем на Vercel/Cloudflare. Pipeline: Стратег → Копирайтер → UX/UI-дизайнер → Frontend, с human gates между этапами.

## Источник

Полный ресёрч в `knowledge/ai-office/multi-agent-landing-research.md` — там методологии, имена, готовые skills, скелеты system-prompts.

## Этап 0 — Установка базового стека skills

Цель: установить все готовые skills, которые покрывают значительную часть работы. Это фундамент.

### 0.1 Установить дизайн-skills

```bash
npx skills add anthropics/skills --skill frontend-design
```
- Официальный от Anthropic, 476k+ установок
- Анти-AI-slop в дизайне, запрещает Inter/Roboto/purple-gradients
- Используется `landing-designer` агентом

### 0.2 Установить маркетинговые skills

```bash
npx skills add coreyhaines31/marketingskills --skill copywriting
npx skills add coreyhaines31/marketingskills --skill marketing-ideas
npx skills add coreyhaines31/marketingskills --skill marketing-psychology
npx skills add coreyhaines31/marketingskills --skill copy-editing
```
- Автор Corey Haines (Swipe Files / Conversion Factory)
- Используется `dr-copywriter` и `behavior-psychologist` (опционально)

### 0.3 Установить advertising-skills (Schwartz-пайплайн)

```bash
npx skills add realkimbarrett/advertising-skills
```
- Пайплайн: avatar-extraction → schwartz-awareness-mapper → mechanism-builder → headline-matrix → objection-crusher → generic-language-killer
- Используется `client-strategist` и `dr-copywriter`

### 0.4 Установить анти-slop skills

```bash
npx skills add https://github.com/hardikpandya/stop-slop --skill stop-slop
npx skills add blader/humanizer@humanizer -g -y
```
- `stop-slop` — score 50, банит em-dash, throat-clearing, rule-of-three
- `humanizer` — 25 категорий AI-паттернов, two-pass self-critique
- Используется `dr-copywriter` после генерации копи

### 0.5 Изучить референс-архитектуру

```bash
git clone https://github.com/zubair-trabzada/ai-marketing-claude /tmp/ai-marketing-ref
```
- Готовая маркетинговая система с 14 sub-skills и 5 параллельными субагентами
- Не интегрировать целиком, использовать как шаблон структуры
- После изучения — `/tmp/ai-marketing-ref` можно удалить

### 0.6 Проверить установку

После всех команд:
- `ls ~/.claude/skills/` — должны быть все установленные skills
- В Claude Code: попросить `/help skills` или попробовать вызвать skill вручную

### 0.7 Прописать правила в CLAUDE.md

Добавить в корневой `CLAUDE.md` секцию:

```markdown
## AI-Office правила (Claude undertriggers по умолчанию)

При работе над лендингом ОБЯЗАТЕЛЬНО использовать соответствующих субагентов:
- На этапе исследования брифа → client-strategist
- На этапе написания текста → dr-copywriter (после него — stop-slop)
- На этапе дизайна → landing-designer + frontend-design skill
- На этапе разработки → frontend-dev

НЕ делать работу субагентов в основной сессии. Каждый агент имеет изолированный контекст и специальные инструменты.
```

## Этап 1 — Создать 4 ядровых субагента

Каждый агент = файл в `.claude/agents/` с YAML-frontmatter + system-prompt. Скелеты в ресёрч-документе.

### 1.1 `client-strategist`

**Файл:** `.claude/agents/client-strategist.md`

**Что делает:** Извлекает из брифа/транскриптов кастдева VoC-фразы, JTBD, awareness-уровень, ключевой angle, список нужных proof-assets.

**Опирается на:**
- Eugene Schwartz «Breakthrough Advertising» (5 awareness levels)
- JTBD Clayton Christensen / Bob Moesta (Forces of Progress)
- Voice-of-Customer extraction
- Skills: `realkimbarrett/avatar-extraction`, `realkimbarrett/schwartz-awareness-mapper`

**Входные данные:** бриф клиента, транскрипт кастдева (markdown с диаризацией)

**Выходные данные:** структурированный brief в формате:
- Avatar (кто клиент)
- Core desire (главное желание)
- Top 3 fears (страхи)
- 10 verbatim VoC phrases (дословные цитаты)
- Awareness level + recommended angle
- Proof assets needed

**Tools:** Read, Glob, Grep, WebSearch, WebFetch
**Model:** sonnet

**Триггеры:** «новый клиент», «бриф», «разбор кастдева», «исследование»

**КРИТИЧНО:** не выдумывать цитаты. Только то что есть в источнике.

### 1.2 `dr-copywriter`

**Файл:** `.claude/agents/dr-copywriter.md`

**Что делает:** Превращает brief стратега в продающий текст лендинга по awareness-структуре, на языке клиента, без AI-звучания.

**Опирается на:**
- Direct response школа: Halbert, Sugarman, Kennedy, Schwartz, Caples
- Фреймворки: PAS, AIDA, BAB, 4 P's, Star-Story-Solution
- Skills: `coreyhaines31/copywriting`, `realkimbarrett/headline-matrix`, `realkimbarrett/objection-crusher`, `stop-slop`, `humanizer`

**Входные данные:** brief от `client-strategist`

**Выходные данные:** полный текст лендинга по структуре:
- Hero (headline + subhead + CTA)
- Problem/agitation block
- Mechanism (как работает решение)
- Proof (доказательства, кейсы, цитаты)
- Offer
- FAQ / objection handling
- Final CTA

**После генерации:** ОБЯЗАТЕЛЬНО прогнать через `stop-slop`. Score < 35 → переписать. Опционально `humanizer` two-pass.

**Tools:** Read, Write, Edit, Skill
**Model:** sonnet

**Триггеры:** «копи», «лендинг текст», «продающий текст», «headline»

**КРИТИЧНО:** использовать VoC-фразы из brief дословно. Не перефразировать в «marketing speak».

### 1.3 `landing-designer`

**Файл:** `.claude/agents/landing-designer.md`

**Что делает:** Превращает копи в конверсионную визуальную структуру и design-spec для разработчика.

**Опирается на:**
- Anthropic `frontend-design` skill (КРИТИЧНО — вызывает первым)
- 7 принципов Cialdini для конверсии
- Z-pattern / визуальная иерархия CTA
- Дизайн-системы: shadcn/ui (база), Aceternity UI / Magic UI (для hero/эффектов), Tailark (marketing-блоки)

**Входные данные:** готовый текст лендинга от `dr-copywriter`

**Выходные данные:** design-spec по секциям:
- Эстетическое направление (одно, смелое, не SaaS-generic)
- Type pairing (НЕ Inter/Roboto)
- Цветовая палитра (CSS vars, контекстная)
- Layout каждой секции
- Размещение Cialdini-триггеров (social proof, scarcity, authority)
- Motion plan (один orchestrated page-load reveal)
- Список нужных компонентов (shadcn base + extensions)

**Tools:** Read, Write, Edit, Skill, Bash
**Model:** sonnet

**Триггеры:** «дизайн лендинга», «UI», «layout», «design»

**КРИТИЧНО:** anti-convergence — каждый проект должен выглядеть ИНАЧЕ. Не клоны.

### 1.4 `frontend-dev`

**Файл:** `.claude/agents/frontend-dev.md`

**Что делает:** Собирает production-лендинг по design-spec, оптимизирует, деплоит.

**Опирается на:**
- Astro (default для контентных лендингов, zero-JS, 95+ Lighthouse)
- Next.js 15/16 (если нужны auth, dynamic data, real-time)
- shadcn/ui + Aceternity/Magic UI компоненты по design-spec
- Skill `vercel/web-design-guidelines` (engineering correctness)
- Core Web Vitals (LCP, INP, CLS)

**Входные данные:** design-spec от `landing-designer`

**Выходные данные:**
- Собранный код лендинга (Astro или Next.js)
- Деплой на Vercel или Cloudflare Pages
- Live URL
- Lighthouse отчёт (≥95 по всем метрикам)

**Tools:** Read, Write, Edit, Bash, Skill
**Model:** sonnet

**Триггеры:** «собрать», «задеплоить», «build», «deploy»

**КРИТИЧНО:** accessibility (semantic HTML, ARIA, labels, alt, focus), SEO (meta, OG, structured data, sitemap), CWV в зелёной зоне.

## Этап 2 — Прогнать на реальном клиенте end-to-end

### 2.1 Выбрать пилотного клиента

После доработки лендинга Никиты-организатора — взять **следующего** клиента из 5 кастдевов (например, Сергея-психолога или Александра-автосервис) и прогнать через AI-офис целиком.

### 2.2 Pipeline

```
1. Бриф + транскрипт кастдева → client-strategist
2. HUMAN GATE #1: проверить инсайты и цитаты (нет ли выдуманных)
3. brief → dr-copywriter (+ stop-slop pass)
4. HUMAN GATE #2: проверить копи на «нейронскость» и попадание в тон
5. копи → landing-designer → design-spec
6. design-spec → frontend-dev → деплой
7. HUMAN GATE #3: финальное ревью + Lighthouse + отправка клиенту
```

### 2.3 Завести `failures.md` для AI-офиса

В `knowledge/ai-office/` создать `failures.md` — отдельный журнал граблей и уроков для AI-офиса (по принципу Компас разработки). Каждая роль накапливает свои ошибки и корректировки.

## Этап 3 — Расширение (после первых 2-3 лендингов)

### 3.1 Добавить `art-director`

**Когда:** когда стоковых/компонентных ассетов перестаёт хватать для премиум-бренда.

**Стек:**
- Replicate MCP (`claude mcp add npx -y replicate-mcp@latest`) — единая интеграция к FLUX.2, Ideogram V3, Recraft, Imagen 4
- Nano Banana MCP — для текста-в-картинке и итеративного редактирования
- ENV: `REPLICATE_API_TOKEN`, `GEMINI_API_KEY`

**Что делает:** генерация hero-визуалов, иллюстраций, иконок, фирменной графики.

### 3.2 Добавить `behavior-psychologist`

**Когда:** когда нужен дополнительный QA-слой убедительности.

**Что делает:** read-only ревьюер. Скорит финальную копи + дизайн по чеклисту 7 принципов Cialdini, проверяет loss-aversion framing, anchoring в pricing, размещение social proof. Выдаёт persuasion-score и список улучшений.

**Запускать как параллельный ревьюер** вместе с `stop-slop` перед финальным human gate.

**Skill:** `coreyhaines31/marketing-psychology` (уже установлен на Этапе 0)

## Метрики качества (после каждого лендинга)

- Lighthouse ≥95 (perf/a11y/SEO/best-practices)
- Core Web Vitals в зелёной зоне
- stop-slop score ≥35/50
- 0 выдуманных цитат в копи
- Awareness-уровень определён и обоснован
- Cialdini-триггеры размещены
- Anti-convergence: проект визуально отличается от предыдущих

## Возможные подводные камни

1. **Subagents undertrigger** — Claude по умолчанию делает всё сам, не делегирует. Решение: явные правила в CLAUDE.md + «pushy» descriptions в YAML-frontmatter каждого агента.
2. **Multi-agent в ~15× дороже по токенам vs обычный чат** — для простых одностраничников иногда дешевле one-shot. Полный pipeline только для серьёзных клиентов.
3. **VoC требует сырья** — стратег бесполезен без реальных транскриптов. Без них — выдуманные инсайты. Human gate #1 обязателен.
4. **Skills frontmatter попадает в system-prompt** — потенциальный prompt-injection. Ревьюить любой скачанный skill перед включением.
5. **AI ≠ замена вкуса** — финальный art-direction и tone остаются за Аликом.

## Триггер для запуска работы

После того как лендинг Никиты-организатора отправлен коучу + получена реакция + понятен finальный формат. Это даст эталон качества, на котором будет калиброваться AI-офис.

## Связь с другими темами в backlog

- Тема «Система генерации лендингов вместо PDF» (2026-05-14) — частично пересекается, эта тема её **развивает и конкретизирует**
- Тема «Возврат к Стратегу DISCOVERY» — после AI-офиса вернёмся, чтобы доразобрать модель услуги
- Тема «Реакции клиентов на PDF» — даст материал для пилотного запуска AI-офиса
