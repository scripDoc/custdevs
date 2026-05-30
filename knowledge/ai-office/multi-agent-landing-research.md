# Мульти-агентная система виртуальных AI-сотрудников в Claude Code для производства продающих лендингов: practical build guide

## TL;DR
- **Стройте на официальном паттерне Anthropic «orchestrator-worker»**: главная Claude Code-сессия = lead-агент (Opus), который последовательно вызывает 4 субагента-специалиста (Sonnet) через `.claude/agents/*.md`. В инженерном блоге Anthropic «How we built our multi-agent research system» прямо указано: «a multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval». Skills (`.claude/skills/`) — это «знания/методологии», subagents — это «роли с изолированным контекстом»; вам нужна **комбинация**: subagents для ролей + skills для методологий внутри каждой роли.
- **Не пишите всё с нуля**: установите готовые проверенные skills (Anthropic `frontend-design` — 476k установок на skills.sh, репозиторий `anthropics/skills` имеет 143k звёзд на GitHub; Corey Haines `marketingskills`; Kim Barrett `advertising-skills` со Schwartz-пайплайном; `stop-slop` против AI-звучания) и допишите 4–6 ролевых субагентов поверх них. Pipeline: Стратег → Копирайтер → UX/UI-дизайнер → Frontend, с человеческим ревью на двух gate-точках (после стратегии и после копирайтинга).
- **Главная ставка на качество**: язык клиента извлекается через Voice-of-Customer / JTBD из транскриптов кастдева, awareness-уровень определяется по Schwartz, дизайн уходит от «AI slop» через `frontend-design` skill, а на деплой идёт Astro (для контентных лендингов, ~95+ Lighthouse, zero-JS) либо Next.js (если нужна интерактивность), на Vercel/Cloudflare Pages.

## Key Findings

1. **Архитектура решена официально.** Anthropic опубликовала инженерный разбор своей multi-agent research system: lead-агент планирует, спавнит субагентов в параллель, каждый со своим context-window, затем синтезирует. Для production они выявили: multi-agent системы используют примерно в 15 раз больше токенов, чем чат-взаимодействия («multi-agent systems use about 15× more tokens than chat interactions»), при этом «token usage explains 80% of performance variance». Вывод: мульти-агент выигрывает ТОЛЬКО когда задача декомпозируется на независимые ветки. Для лендинга задачи в основном **последовательны** (стратегия→копи→дизайн→код), поэтому Алику нужен sequential-pipeline, а параллелизм — только внутри research-фазы.

2. **Skills vs Subagents — это разные инструменты.** Subagent = именованный изолированный Claude со своим system-prompt, context-window, набором tools (файл `.claude/agents/name.md` с YAML-frontmatter). Skill = markdown-инструкция (`SKILL.md`), которую Claude динамически подгружает по описанию (progressive disclosure: метаданные→тело→ресурсы). Рекомендация Anthropic: «one skill, one job»; описания делать «pushy», иначе Claude undertriggers (по словам skill-creator от Anthropic, «Claude has a tendency to 'undertrigger' skills — to not use them when they'd be useful»). Для проекта Алика: **роли = субагенты, методологии = skills**, плюс CLAUDE.md с явными правилами делегирования.

3. **Готовые маркетинговые skills уже покрывают значительную часть работы.** `coreyhaines31/marketingskills` (CRO, copywriting, marketing-psychology, ~4.8k⭐, автор Corey Haines — Swipe Files / Conversion Factory) и `realkimbarrett/advertising-skills` Кима Барретта (avatar-extraction → offer-extraction → schwartz-awareness-mapper → mechanism-builder → headline-matrix → objection-crusher → generic-language-killer) — это готовый direct-response пайплайн на методологии Schwartz.

4. **Против «AI slop» есть конкретные инструменты.** Для текста — `stop-slop` (банит em-dash, throat-clearing openers, rule-of-three, даёт score из 50) и `humanizer` (25 категорий паттернов, two-pass self-critique). Для дизайна — Anthropic `frontend-design` явно запрещает Inter/Roboto/Arial, purple-gradient-on-white, cookie-cutter SaaS-layouts и требует «NEVER converge on common choices (Space Grotesk, for example) across generations».

## Details

### РОЛЬ 1: СТРАТЕГ-ИССЛЕДОВАТЕЛЬ КЛИЕНТА

**Зона ответственности:** Извлечь из брифа/транскриптов кастдева корневые мотивы, страхи, язык клиента; определить awareness-уровень аудитории; выдать структурированный brief для копирайтера.

**Методологии:**
- **Jobs To Be Done (JTBD)** — Clayton Christensen / Bob Moesta. Фокус: «push of the situation» и «pull», struggling moment, forces of progress (push, pull, anxiety, habit). Для извлечения VoC из транскрипта: data-coding построчно — кодировать ключевые фразы, эмоции, паттерны поведения, затем группировать в темы (deductive подход по JTBD-этапам). Совет из практики: задавать вопросы «как/что», а не «почему»; «играть в незнайку», чтобы клиент объяснял своими словами.
- **Eugene Schwartz, «Breakthrough Advertising» (1966), 5 awareness levels:** Unaware → Problem-Aware → Solution-Aware → Product-Aware → Most Aware. Schwartz распределял аудиторию примерно так: problem-aware ~20%, solution-aware ~10%. Каждому уровню — свой угол копи. Плюс концепт market sophistication (5 стадий). Ключевая цитата Schwartz: «Copy is not written. Copy is assembled… you are building a little city of desire».
- **Voice-of-Customer (VoC):** ключевой принцип Gary Halbert из Boron Letters — «смотри что люди ПОКУПАЮТ, а не что говорят». Извлекать эмоционально заряженный язык в точных, дословных формулировках клиента и переносить в самые слабые секции копи.

**Готовые skills/agents для установки:**
- `npx skills add coreyhaines31/marketingskills --skill marketing-ideas` (+ market research)
- `avatar-extraction` и `schwartz-awareness-mapper` из `realkimbarrett/advertising-skills`
- VoltAgent `market-researcher` субагент (`claude plugin marketplace add VoltAgent/awesome-claude-code-subagents`)
- Инструменты транскрипт-анализа: Insight7 (theme extraction), Otter.ai (speaker ID), Dovetail/NVivo (coding)

**Скелет system-prompt субагента (`.claude/agents/strategist.md`):**
```
---
name: client-strategist
description: Use PROACTIVELY at the start of any landing page project to extract customer insights from briefs, transcripts, and discovery calls. Triggers on "new client", "research", "discovery", "кастдев", "бриф".
tools: Read, Glob, Grep, WebSearch, WebFetch
model: sonnet
---
You are a customer-research strategist trained in JTBD (Christensen/Moesta) and Eugene Schwartz's 5 awareness levels.
Given a brief or call transcript:
1. Code the transcript line-by-line: tag pains, desired outcomes, anxieties, objections, and EXACT verbatim phrases (Voice of Customer).
2. Build a JTBD statement + Forces of Progress (push/pull/anxiety/habit).
3. Determine the audience awareness level (Unaware→Most Aware) and market sophistication stage.
4. Output a STRICT template: Avatar | Core desire | Top 3 fears | 10 verbatim VoC phrases | Awareness level + recommended angle | Proof assets needed.
NEVER invent quotes. Only use language present in source material.
```

**Точки взаимодействия:** передаёт копирайтеру VoC-фразы + awareness level + angle. Получает бриф от человека.

**Метрики:** ≥10 дословных VoC-фраз; awareness-уровень определён и обоснован; 0 выдуманных цитат (проверяется человеком на gate #1).

### РОЛЬ 2: DIRECT RESPONSE COPYWRITER

**Зона ответственности:** Превратить brief стратега в продающий текст лендинга на ЯЗЫКЕ клиента, по правильной awareness-структуре, без AI-звучания.

**Методологии и фреймворки:**
- **PAS (Problem-Agitate-Solution)** — популяризован Dan Kennedy в «The Ultimate Sales Letter» (1990), назвал «the most reliable sales formula ever invented». Опирается на loss aversion: «people are more likely to act to avoid pain than to get gain». Лучшая для ситуаций, где боль уже ощущается. Принцип: «Specificity is the agitation» — конкретные числа вместо размытых заявлений.
- **AIDA** (Attention-Interest-Desire-Action) — приписывается E. St. Elmo Lewis, 1898; основной фреймворк Gary Halbert.
- **BAB** (Before-After-Bridge), **4 P's** (Promise-Picture-Proof-Push), **Star-Story-Solution**.
- **Легенды для system-prompt'ов:** Gary Halbert (conversational tone, Boron Letters, «King of Copy»), Joe Sugarman (slippery slide, эмоции, Adweek Copywriting Handbook), Dan Kennedy (PAS, bold offers), John Caples (headlines, «They Laughed When I Sat Down at the Piano…»), Claude Hopkins (split-testing, Scientific Advertising), Eugene Schwartz (mass desire).
- **Письмо на языке клиента:** использовать VoC-фразы дословно (НЕ перефразировать в «marketing speak»); параметры voice по Nicola Moors / Copyhackers: tone, sentence length, language/vocabulary, style. Совет Gary Provost для ритма: «vary sentence length — short, medium and long — write in a way that sounds like music».

**Против AI slop:**
- `stop-slop` (Hardik Pandya): `npx skills add https://github.com/hardikpandya/stop-slop --skill stop-slop`. Банит em-dash, throat-clearing openers, бинарные контрасты, rule-of-three, pull-quote phrasing. Score из 50, ниже 35 = переписать.
- `humanizer` (blader): `npx skills add blader/humanizer@humanizer -g -y`. 25 категорий, two-pass self-critique, добавляет voice, а не только убирает паттерны.
- `realkimbarrett/generic-language-killer`.

**Готовые skills:**
- `npx skills add coreyhaines31/marketingskills --skill copywriting copy-editing`
- `realkimbarrett/advertising-skills` (полный copy-chief пайплайн: headline-matrix, mechanism-builder, objection-crusher)
- VoltAgent `copywriter-specialist`, `content-marketer` субагенты

**Скелет system-prompt:**
```
---
name: dr-copywriter
description: Use to write or rewrite landing page copy. Triggers on "copy", "headline", "sales page", "продающий текст", "лендинг текст".
tools: Read, Write, Edit, Skill
model: sonnet
---
You are a direct-response copywriter in the lineage of Halbert, Sugarman, Kennedy, Schwartz, Caples.
INPUT: the strategist's brief (VoC phrases, awareness level, angle, proof).
RULES:
1. Match copy structure to awareness level (Schwartz): unaware→story/problem; solution-aware→lead with mechanism; most-aware→offer+urgency.
2. Use the client's EXACT verbatim VoC phrases. Do not paraphrase them into "marketing speak".
3. Choose ONE framework per section (PAS for problem blocks, AIDA for hero, 4Ps for offer).
4. After drafting, run the stop-slop skill. No em-dashes, no throat-clearing, vary sentence length, two items beat three.
5. Specificity is the agitation: concrete numbers > vague claims.
OUTPUT: hero (headline+subhead+CTA), problem/agitation, mechanism, proof, offer, FAQ/objections, final CTA.
```

**Точки взаимодействия:** получает от стратега brief; отдаёт дизайнеру готовую копи с пометкой секций и иерархии. Человеческое ревью на gate #2.

**Метрики:** stop-slop score ≥35/50; все VoC-фразы использованы дословно; awareness-структура соблюдена; есть headline-matrix (≥5 вариантов).

### РОЛЬ 3: UX/UI-ДИЗАЙНЕР ЛЕНДИНГОВ

**Зона ответственности:** Превратить копи в конверсионную визуальную структуру и production-grade UI, уникальный (не клон), без AI-эстетики.

**Готовые skills (ставить в первую очередь):**
- **Anthropic `frontend-design`** (официальный, 476k установок на skills.sh): `npx skills add anthropics/skills --skill frontend-design`. Заставляет коммититься в BOLD-эстетику ДО кода: Purpose→Tone(extreme)→Intelligence→Differentiation. Запрещает Inter/Roboto/Arial, purple-gradients, emojis-as-icons. «NEVER converge on common choices (Space Grotesk) across generations» — это и есть anti-convergence logic.
- **Vercel `web-design-guidelines`** (vercel-labs/agent-skills, ~19.5k⭐): 100+ правил accessibility/performance/UX, ревью существующего кода.
- **UI/UX Pro Max** (anthropic-frontend-design fork): Python CLI `scripts/search.py --design-system` — БД из 50+ UI-стилей, 97 палитр, 57 font-pairings, 99 UX-guidelines, 25 chart-types, 9 стеков.
- **Impeccable** (impeccable.style): 1 skill + 23 команды + детектор anti-паттернов (41 deterministic rule, no LLM, exit codes для CI).
- **Bencium** UX skills (controlled + innovative, >28k символов).

**Дизайн-системы / библиотеки компонентов:**
- **shadcn/ui** — база (Radix + Tailwind, backed by Vercel), для app-частей и кастомных design-систем.
- **Aceternity UI** (~28k⭐, ui.aceternity.com) — анимированные компоненты для лендингов (Framer Motion/Motion); 3D-карты, spotlight, beams. All-Access $249. ⚠️ 3D-компоненты тянут Three.js (~600KB) — годятся для marketing-страницы, но не в основной app-бандл.
- **Magic UI** — polished micro-interactions, marketing-анимации; Pro-tier с AI-Agent landing templates.
- **Tailark** (300+ marketing-блоков, 4 темы Quartz/Dusk/Mist/Veil) — наименее «generic» для лендингов.
- Для quick-validation: Launch UI / leoMirandaa (free, MIT). Паттерн 2026: валидировать копи на free-шаблоне → апгрейд на Magic UI Pro/Aceternity, когда messaging доказан.

**Принципы конверсионного дизайна:** Cialdini (7 принципов: reciprocity, scarcity, authority, commitment/consistency, social proof, liking, unity) — закладывать в layout: social proof блоки, scarcity на CTA, authority-символы (награды/логотипы), micro-commitments в формах. Z-pattern / визуальная иерархия для CTA. Progressive disclosure, чтобы не перегружать.

**Что отличает senior-дизайн от AI slop:** characterful типографика (display + refined body), доминирующие цвета с резкими акцентами (не timid evenly-distributed), асимметрия/overlap, ОДИН хорошо оркестрированный page-load со staggered reveals (animation-delay 150–300ms), SVG-иконки (не emoji), cursor-pointer на интерактиве, labels на inputs, alt на images.

**Скелет system-prompt:**
```
---
name: landing-designer
description: Use to design landing page UI from finished copy. Triggers on "design", "layout", "UI", "дизайн лендинга".
tools: Read, Write, Edit, Skill, Bash
model: sonnet
---
You are a senior landing-page designer. ALWAYS invoke the frontend-design skill first.
1. Commit to ONE bold aesthetic direction tied to the client's brand/audience (not generic SaaS).
2. Map copy sections to a conversion layout; place CTAs on the Z-path; embed Cialdini triggers (social proof, scarcity, authority).
3. Pick distinctive type pairing + context-specific palette (CSS vars). NO Inter/Roboto/purple-gradients.
4. Specify motion: one orchestrated page-load reveal; 150-300ms micro-interactions.
5. Output: section-by-section design spec + component choices (shadcn base + Aceternity/Magic UI for hero/effects).
Each project must look DIFFERENT from the last. No convergence.
```

**Точки взаимодействия:** получает копи от копирайтера; отдаёт design-spec + выбор компонентов frontend-разработчику; запрашивает у Арт-директора визуалы (если роль активна).

**Метрики:** проходит Impeccable-детектор (41 правило); уникальность vs прошлые проекты; Cialdini-триггеры размещены; accessibility-базис (labels/alt/contrast).

### РОЛЬ 4: FRONTEND-РАЗРАБОТЧИК

**Зона ответственности:** Собрать production-лендинг по design-spec, оптимизировать performance/SEO/accessibility, задеплоить.

**Стек (решение по типу лендинга):**
- **Astro** — дефолт для контентных лендингов: zero-JS by default, Lighthouse ~95+ (vs Next.js static ~80–85), ~40% быстрее загрузка, ~90% меньше JS. 16 января 2026 Cloudflare официально объявила, что команда The Astro Technology Company переходит в Cloudflare (CEO Matthew Prince: «we're going to ensure Astro continues to be the best web framework for content-driven websites»); Astro 6 Beta (январь 2026) добавил dev-сервер на workerd и first-class поддержку Cloudflare Workers. Islands-архитектура для точечной интерактивности (форма, pricing-toggle). Деплой на любой CDN бесплатно.
- **Next.js 15/16** — когда нужны auth, dynamic data, сложный state, real-time. Turbopack по дефолту, PPR стабилизирован. Глубже всего на Vercel.
- Частый паттерн: Astro для marketing-сайта (`www.`) + Next.js для app (`app.`).

**Performance/SEO/Accessibility:** Core Web Vitals (LCP, INP, CLS) как ranking-сигнал. Производительность напрямую влияет на конверсию: по данным Aberdeen Group, задержка в 1 секунду вызывает «a 7% drop in conversions, 11% fewer page views, and a 16% dip in customer satisfaction» (отдельная часто цитируемая цифра Google: 53% мобильных пользователей покидают сайт, грузящийся дольше 3с). Astro даёт near-perfect CWV «из коробки». Структурированные данные, мета, OG-теги, hreflang (Astro Content Collections).

**Деплой workflow:**
- **Cloudflare Pages** — бесплатно для static Astro, edge-доставка.
- **Vercel** — глубже всего с Next.js (edge functions, image optimization, analytics).
- **Netlify** — альтернатива.
- Astro static: `npm run build` → drag `dist/` на любой хост.

**Готовые skills:** Vercel `web-design-guidelines` (engineering correctness), VoltAgent `frontend-developer` субагент, `geo-seo-claude`/`seo-geo-claude-skills` для SEO.

**Скелет system-prompt:**
```
---
name: frontend-dev
description: Use to build and deploy the production landing page from a design spec. Triggers on "build", "implement", "deploy", "собрать", "задеплоить".
tools: Read, Write, Edit, Bash, Skill
model: sonnet
---
You build production landing pages.
1. Default to Astro for content landing pages (zero-JS, 95+ Lighthouse); use Next.js only if auth/dynamic/real-time is required.
2. Use shadcn/ui base + Aceternity/Magic UI for hero effects per the design spec.
3. Enforce Core Web Vitals: optimize LCP image, avoid layout shift, lazy-load below fold, ship minimal JS (islands).
4. Accessibility: semantic HTML, ARIA, labels, alt, focus states.
5. SEO: meta, OG, structured data, sitemap.
6. Deploy: Cloudflare Pages (static Astro) or Vercel (Next.js). Run Vercel web-design-guidelines skill as a final review.
```

**Точки взаимодействия:** получает design-spec от дизайнера; возвращает live-URL + Lighthouse-отчёт. Финальное человеческое ревью перед публикацией.

**Метрики:** Lighthouse ≥95 (perf/a11y/SEO/best-practices); CWV в зелёной зоне; проходит Vercel web-design-guidelines.

### РОЛЬ 5: АРТ-ДИРЕКТОР (опционально)

**Когда нужен vs UX-дизайнер:** UX-дизайнер отвечает за структуру/конверсию/layout; Арт-директор — за визуальный язык, иллюстрации, мудборды, фирменную графику, кастомные hero-визуалы и иконографику, когда стоковых/компонентных ассетов недостаточно для премиум-бренда.

**AI-генерация (актуальные модели, состояние на май 2026):**
- **Midjourney V8.1** (релиз на midjourney.com 30 апреля 2026; по официальной документации — «our fastest model so far. Standard jobs render about 4–5 times faster than earlier versions», HD/native 2K по умолчанию) — артистичные/кинематографичные hero-визуалы, mood/concept exploration. ⚠️ Нет официального публичного API — для автоматизации использовать через Replicate или замену. Слабое место — текст в изображении.
- **Google Nano Banana** (Gemini image): Nano Banana Pro (Gemini 3 Pro Image, до 4K, «the best model for creating images with correctly rendered and legible text»), Nano Banana 2 (Gemini 3.1 Flash Image) — лучший выбор для текста-в-картинке + итеративного редактирования + локализации. ~$0.04–0.05/изобр, до ~$0.15–0.24 на 4K. Требует платный Gemini API tier; SynthID watermark.
- **Imagen 4** (Google, Vertex): `imagen-4.0-ultra-generate-001` ($0.06, native 2K), Standard `imagen-4.0-generate-001` ($0.04), Fast `imagen-4.0-fast-generate-001` ($0.02) — photoreal продуктовая графика, print-ready.
- **OpenAI gpt-image-1.5** (16 дек 2025, «makes precise edits while keeping details intact, and generates images up to 4x faster») / `gpt-image-2` (`gpt-image-2-2026-04-21`, до 3840×2160) — instruction-following, редактирование, sketch→graphic.
- **FLUX.2** (Black Forest Labs, 25 ноя 2025; варианты Pro/Flex/Dev/Klein, Klein под Apache 2.0) и FLUX.1 Kontext — консистентность персонажа/объекта/стиля через multi-turn edits, open-weights.
- **Ideogram V3** (26 мар 2025) — лучший для текста-в-изображении/логотипов (~90–95% точность текста). API ~$0.06/изобр; до 3 style-reference изображений, Style Codes для brand-консистентности.
- **Recraft V3/V4** — единственный major-инструмент для native SVG (логотипы, иконки, brand-ассеты, scalable вектор + readable text). Плагины для Figma/Framer.

**Матрица:** Midjourney = арт-hero; Imagen / Nano Banana = photoreal + текст + 4K + диалоговое редактирование; gpt-image = instruction-following; FLUX = консистентное редактирование; Ideogram = текст/логотипы; Recraft = вектор/SVG.

**Inspiration-галереи (мудборды/референсы):**
- **Awwwards** (awwwards.com) — самая престижная награда, экспериментальные сайты.
- **Godly** (godly.website) — лучшая free-галерея для motion/scroll-дизайна, tech/SaaS.
- **Land-book** (land-book.com) — SaaS/startup лендинги по стилю/цвету/паттерну; для conversion-блоков.
- **Lapa Ninja** (lapa.ninja) — 7300+ лендингов + 15000+ скриншотов, фильтры по категориям.
- **Mobbin** (mobbin.com) — крупнейшая библиотека реальных production UI (1200+ apps), для UX-паттернов.
- **SaaS Landing Page** (saaslandingpage.com), **Refero** (refero.design), **Httpster** (httpster.net — минимал/типографика), SiteInspire, One Page Love.

**Claude Code skills/MCP для визуалов:**
- **Replicate MCP** (официальный, mcp.replicate.com) — один endpoint к FLUX.2, Ideogram V3, Recraft, Imagen 4, SDXL: `claude mcp add` с `npx -y replicate-mcp@latest`, env `REPLICATE_API_TOKEN`. Tools: `search_models`, `create_predictions`. **Лучшая single-интеграция** для арт-директора (Midjourney без API → через Replicate-обёртки).
- **Nano Banana MCP** (ConechoAI/Nano-Banana-MCP): npx-сервер с `generate_image`/`edit_image`/`continue_editing` + multiple reference images для style transfer. Требует `GEMINI_API_KEY`.
- **Nano Banana skill** через Gemini CLI: `gemini extensions install https://github.com/gemini-cli-extensions/nanobanana`.

**Скелет:** субагент `art-director` с Replicate MCP + Nano Banana, на вход — design-spec + brand-палитра, на выход — hero-визуалы/иконки/иллюстрации в `/public/assets`.

### РОЛЬ 6: ПСИХОЛОГ ПОВЕДЕНИЯ / НЕЙРОМАРКЕТОЛОГ (опционально)

**Зона ответственности:** QA-слой убедительности — проверять копи и дизайн на наличие и корректность поведенческих триггеров.

**Принципы:**
- **Cialdini, «Influence» + «Pre-Suasion»:** 7 принципов (reciprocity, commitment/consistency, social proof, authority, liking, scarcity, unity).
- **Kahneman, «Thinking Fast and Slow»:** System 1/System 2; loss aversion (мы движемся ОТ боли сильнее, чем К выгоде — основа PAS); anchoring (для pricing); framing.
- Когнитивные искажения: FOMO/scarcity, bandwagon (social proof), authority bias, anchoring на pricing, von Restorff effect (выделение CTA).

**Готовый skill:** `coreyhaines31/marketing-psychology` — «Apply psychological principles and behavioral science to copy and design».

**Скелет:** субагент-ревьюер (read-only), который скорит финальную копи+дизайн по чеклисту из 7 принципов Cialdini + проверяет loss-aversion framing, anchoring в pricing, размещение social proof; выдаёт persuasion-score и список улучшений. Запускать как параллельный ревьюер вместе с stop-slop перед финальным gate.

### МЕТА: МУЛЬТИ-АГЕНТНАЯ АРХИТЕКТУРА В CLAUDE CODE

**Что выбрать Алику:** комбинацию. Subagents (`.claude/agents/`) для 4–6 ролей (изоляция контекста, свои tools), skills (`.claude/skills/`) для методологий внутри ролей, CLAUDE.md как orchestration-конфиг с явными правилами делегирования (Claude undertriggers субагентов по умолчанию — нужны явные инструкции «Use X agent to…»).

**Pipeline (sequential, т.к. задачи зависимы):**
```
Человек: "Сделай лендинг для клиента X" + бриф/транскрипт
   ↓
[client-strategist] → VoC-фразы, awareness, angle, proof-list
   ↓ ⚑ HUMAN GATE #1 (проверка инсайтов и цитат)
[dr-copywriter] → копи по awareness-структуре, + stop-slop
   ↓ (параллельно: [behavior-psychologist] скорит убедительность)
   ↓ ⚑ HUMAN GATE #2 (проверка копи и tone)
[landing-designer] (+ [art-director] для визуалов) → design-spec + ассеты
   ↓
[frontend-dev] → Astro/Next.js сборка + деплой Cloudflare/Vercel
   ↓ ⚑ HUMAN GATE #3 (финальное ревью + Lighthouse)
   ↓
Live URL
```

**Передача контекста:** lead-агент собирает summary каждого субагента (субагенты возвращают только итог, не intermediate-шум — рекомендация core-инженера Claude Code Adam Wolf: «sub agents work best when they just look for information and provide a small amount of summary back to main conversation thread»). Для длинных проектов — shared memory (`memory: user` во frontmatter, `~/.claude/agent-memory/`) или общий `/docs/brief.md` файл, который читают все роли.

**Sequential vs parallel:** для лендинга — sequential (каждый шаг зависит от предыдущего). Parallel только внутри research-фазы стратега (искать несколько источников/конкурентов) и для QA-ревьюеров (stop-slop + behavior-psychologist параллельно). Anthropic-практики: спавнить 3–5 субагентов в research-параллель максимум; не over-делегировать простые задачи; чёткие output-форматы для лёгкого синтеза.

**Где брать config:** `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-4-5` для субагентов (lead на Opus); `/agents` команда для создания; restart сессии, если правишь файлы напрямую (агенты загружаются при старте сессии).

### МЕТА: ТОПОВЫЕ ИСТОЧНИКИ И ПЛАТФОРМЫ

- **Anthropic:** официальный блог engineering (anthropic.com/engineering/multi-agent-research-system), `github.com/anthropics/skills` (143k⭐, 16.9k форков), docs code.claude.com.
- **GitHub awesome-репы:** `VoltAgent/awesome-claude-code-subagents` (154+ субагентов), `VoltAgent/awesome-agent-skills` (1000+ skills), `jqueryscript/awesome-claude-code`, `coreyhaines31/marketingskills`, `zubair-trabzada/ai-marketing-claude` (15 skills + 5 parallel субагентов: market-landing, market-copy и т.д.), `realkimbarrett/advertising-skills`, `hardikpandya/stop-slop`, `shannhk/avoid-slop`.
- **Skills-маркетплейсы/директории:** skills.sh (Vercel-backed, `npx skills add`), officialskills.sh, ClaudeSkills.info (658+ free), claudemarketplaces.com (6700+ skills), MCP Market (mcpmarket.com), Smithery (smithery.ai), Agensi (security-scanned, paid).
- **Сообщества:** Reddit r/ClaudeAI, r/ClaudeCode (где экспериментируют практики).
- **Имена/проекты, задающие планку:** Adam Wolf (core engineer Claude Code); Corey Haines (Swipe Files / Conversion Factory — marketingskills); Kim Barrett (advertising-skills); создатели Aceternity (@mannupaaji), Impeccable.

### МЕТА: ПРАКТИЧЕСКИЕ ПРИМЕРЫ И БЕНЧМАРКИ

- **Реальные кейсы:** «Shipped a landing page in 2 hours using Conductor & Impeccable» (отзыв на impeccable.style); множество отзывов о frontend-design skill, дающем результат уровня «components that look like a senior designer reviewed them».
- **Готовая marketing-система-референс:** `zubair-trabzada/ai-marketing-claude` — оркестратор `/market` + 14 sub-skills (включая market-landing для CRO) + 5 параллельных субагентов — прямой шаблон архитектуры для Алика.
- **Бенчмарки качества:** Lighthouse ≥95; Core Web Vitals (зелёные LCP/INP/CLS); stop-slop ≥35/50; Impeccable детектор (41 правило, exit codes для CI); Anthropic multi-agent eval (+90,2% при правильной декомпозиции).

## Recommendations

**Этап 0 — фундамент (день 1):**
1. Установить базовый стек skills: `npx skills add anthropics/skills --skill frontend-design`; `npx skills add coreyhaines31/marketingskills`; `npx skills add https://github.com/hardikpandya/stop-slop --skill stop-slop`; `npx skills add blader/humanizer@humanizer -g -y`.
2. Установить `realkimbarrett/advertising-skills` (Schwartz-пайплайн) и изучить `zubair-trabzada/ai-marketing-claude` как референс-архитектуру.
3. Прописать в CLAUDE.md правила делегирования (явные «Use X agent…», т.к. Claude undertriggers).

**Этап 1 — собрать 4 ядровых субагента (дни 2–4):** создать `.claude/agents/`: client-strategist, dr-copywriter, landing-designer, frontend-dev по скелетам выше. Каждый — на Sonnet, lead-сессия на Opus. Создать общий `/docs/brief.md` для передачи контекста.

**Этап 2 — прогнать на реальном клиенте (дни 5–7):** один лендинг end-to-end с 3 human-gates. Завести `failures.md` (по методологии Компас) для накопления ошибок каждой роли.

**Этап 3 — расширение (после первых 2–3 лендингов):** добавить art-director (Replicate MCP + Nano Banana) и behavior-psychologist (marketing-psychology skill, read-only ревьюер), когда базовый pipeline стабилен.

**Пороги для изменения подхода:**
- Если субагенты не триггерятся → сделать описания «pushy» + явные правила в CLAUDE.md.
- Если токены/стоимость растут → понизить субагентов на Haiku для read-only research, оставить Sonnet на генерацию (помните: multi-agent ≈ 15× токенов чата).
- Если контекст переполняется → перейти на shared memory / `/docs` файлы вместо длинных возвратов.
- Если копи всё равно звучит «нейросеточно» → ужесточить stop-slop, добавить больше VoC-дословных фраз, прогнать humanizer two-pass.
- Если дизайны конвергируют (похожи) → усилить anti-convergence в frontend-design prompt, явно требовать разные темы/шрифты per project.

## Caveats

- **Мульти-агент дорог:** ≈15× токенов vs обычный чат (данные Anthropic), и токены объясняют ~80% вариации качества. Для простых одностраничников иногда дешевле one-shot в main-сессии с skills, без субагентов. Включайте полный pipeline только когда задача того стоит.
- **Subagents undertrigger:** Claude по умолчанию делает всё сам («это легко, я сам»). Без явных правил в CLAUDE.md армия субагентов простаивает.
- **Midjourney без официального API** — для автоматической генерации использовать Replicate-обёртку или Nano Banana/Imagen/FLUX/Ideogram/Recraft, у которых API есть.
- **Очень свежие версии моделей** (Midjourney V8.1, gpt-image-2, Nano Banana 2 — все весна 2026) меняются быстро; точные даты/цены проверяйте перед продакшеном. Точная дата Nano Banana 2 (26 фев 2026) подтверждена вторичным источником, а не напрямую Google (Google подтверждает запуск и идентичность Gemini 3.1 Flash Image, но точную календарную дату я напрямую от Google не верифицировал).
- **Безопасность skills:** ревьюить любой скачанный skill перед включением (frontmatter попадает в system-prompt → риск prompt-injection). Использовать security-scanned маркетплейсы (Agensi) для paid-skills.
- **VoC требует сырья:** стратег-агент бесполезен без настоящих транскриптов кастдева/отзывов. Без них он сгенерирует правдоподобные, но выдуманные инсайты — отсюда обязательный human gate #1.
- **AI ≠ замена вкуса:** даже frontend-design и Nano Banana дают «good enough to ship», а не Series-A-pitch-grade бренд. Финальный art-direction и tone остаются за человеком (Аликом).