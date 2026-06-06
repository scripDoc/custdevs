# _sites_registry — реестр задеплоенных лендингов офиса

Источник истины по тому, какой деплой жив, какой заморожен, какой отправлен клиенту. Один лендинг может иметь несколько версий-деплоев (разные проекты Vercel / URL). **Правило фриза:** деплой со статусом `frozen` НЕ трогаем — ни пуша, ни редеплоя, ни смены алиаса; новые версии идут ОТДЕЛЬНЫМ проектом/URL.

## Статусы

- `current` — актуальная рабочая версия (на неё ведём дальнейшие правки).
- `honest` — прошла честную пересборку (память/фазы/метрики приведены к реальности). Может стоять вместе с `current`.
- `sent` — отправлена клиенту (зафиксировано касание).
- `frozen` — заморожена, правки/редеплой запрещены (обычно = `sent` + есть новая версия).
- `live` — задеплоена и доступна по URL.
- `draft` — собрана локально, ещё не задеплоена.

## Реестр

| Клиент (slug) | Версия | Проект Vercel | projectId | URL | Статус | Дата | Заметка |
|---|---|---|---|---|---|---|---|
| nikita_muzh_klub | v6 (честная) | `arhiv-sistemy` | `prj_LrbzsjodlGWmk5AlTEg4b7ADolWO` | https://arhiv-sistemy.vercel.app/ | `live` · `honest` · `current` | 2026-06-06 | **Честная v6 задеплоена в прод существующего проекта — URL у клиента прежний.** v5 заменён (память=траектория, фазы MVP/Ф2/Ф3, убрано «минуту вместо получаса», конфляция «8» снята). qa PASS (`_qa_report_v6.md`). Deploy id `dpl_9ix4j8QB4uPZxRWbdJXWwbAgChxm`. Папка-деплой: `deliverables/nikita_muzh_klub/` (og:url=arhiv). noindex. |
| nikita_muzh_klub | v5 (исходная) | `arhiv-sistemy` | `prj_LrbzsjodlGWmk5AlTEg4b7ADolWO` | (был live до 2026-06-06) | `superseded` · откатимо | 2026-06-01→06-06 | Был live на arhiv-sistemy до замены на честную v6. **Снапшот для отката:** `deliverables/nikita_muzh_klub_v5_frozen/` (+ Vercel deployment history). Источники: `clients/nikita_muzh_klub/{copywriter_draft_v5_sent_frozen.md, product_spec_brief_v2_sent_frozen.md}`. QA-блок (память как готовая) — причина замены. |
| nikita_muzh_klub | v6 (стейджинг) | `poryadok-iz-haosa` | _(не создан — не деплоился)_ | (без живого URL) | `superseded` | 2026-06-05→06-06 | Был стейджинг-источник честной v6 (отдельный URL). После решения «честный контент на СТАРЫЙ URL» — **superseded**: контент уехал в `arhiv-sistemy`. Новый проект/URL НЕ создавать. Папка `deliverables/poryadok-iz-haosa/` оставлена как референс (og:url=poryadok, в прод не идёт). |
| sergey_psiholog | v1 (первый прогон Директора) | `tsifrovoy-sarafan` | `prj_2UYKXUk06C8wzgGM7jiD2ZKMguyP` | https://tsifrovoy-sarafan.vercel.app | `live` · `prod` | 2026-06-06 | **Прод по явному «го» Алика** (стоп «только превью» снят сознательно). `vercel --prod` → чистый публичный URL (HTTP 200, без auth-валла). Live-проверка: noindex+robots.txt стоят, имя/slug клиента 0 утечек, title нейтральный. Нейтральный slug. Оба гейта честности PASS. Папка: `deliverables/tsifrovoy-sarafan/`. Клиенту ещё НЕ отправлен (нет статуса `sent`). CTA живой → `t.me/alik_x_now` (из env `TELEGRAM_URL`, target=_blank), доводчик обновлён 2026-06-06; передеплоен. Чужой `arhiv-sistemy` не тронут. |

## История касаний / переходов

- **2026-06-01** — v5 (`arhiv-sistemy`) задеплоена и отправлена клиенту.
- **2026-06-02** — QA-controller: BLOCK по оси «фабрикация» (сквозная память подана как рабочая, в железе — нет). Лендинг заморожен, правка отложена до разморозки (`clients/nikita_muzh_klub/_qa_report.md`).
- **2026-06-05** — собрана честная v6 на НОВОМ обезличенном URL `poryadok-iz-haosa` (отдельный проект Vercel, старый не тронут). Фикс прошёл по цепочке: spec_brief → копи → деплой-папка. Ждёт ревью Алика → деплой.
- **2026-06-05** — qa-controller (READ-ONLY) повторно прогнан по v6: вердикт **PASS**, переход BLOCK→PASS подтверждён (память=траектория, 0 фабрикаций, slop/приватность чисто; 3 низких карри-овера под «ПРИМЕР» — не блокеры). Отчёт: `clients/nikita_muzh_klub/_qa_report_v6.md`. Деплой по-прежнему ждёт «го» Алика.
- **2026-06-06** — **решение Алика: честный контент v6 на СТАРЫЙ URL** (без новой ссылки). Фриз arhiv-sistemy снят сознательно. v6 (из `poryadok-iz-haosa`, og:url переставлен на arhiv) задеплоен `--prod` в существующий проект `arhiv-sistemy` (id `prj_LrbzsjodlGWmk5AlTEg4b7ADolWO`), URL прежний `https://arhiv-sistemy.vercel.app/`. Третий проект НЕ создавался. v5 снапшотнут в `deliverables/nikita_muzh_klub_v5_frozen/` (откатимо). Live-проверка: память-как-готовое/«получаса»/«пять-десять» = 0; траектория/фазы/og:url=arhiv/noindex — на месте. `poryadok-iz-haosa` → superseded.
- **2026-06-06** — `sergey_psiholog`: первый автономный прогон Директора собрал лендинг в `deliverables/tsifrovoy-sarafan/` и задеплоил **превью** (`vercel --yes`, без `--prod`). Нюанс: первый деплой нового проекта Vercel авто-промоутился в prod (поведение CLI, не флаг) → фронтендер откатил (`vercel remove`), пересобрал в preview; production теперь пуст. Превью за Deployment Protection (401). Оба гейта честности PASS. Публичная отдача/прод — по «го» Алика. См. `failures.md` (#vercel #deploy auto-promote).
- **2026-06-06** — `sergey_psiholog` → **прод по «го» Алика**: `vercel --prod` → публичный `https://tsifrovoy-sarafan.vercel.app` (HTTP 200). Затем фикс мёртвых CTA: обе кнопки «Созвонимся…» были на `href="#"` → проставлен живой `TELEGRAM_URL` (`t.me/alik_x_now`, target=_blank rel=noopener), доводчик hero «разойдёмся друзьями» → «Без давления — просто посмотрим, твоё или нет.»; передеплой прода, live-проверка curl (кнопки живые, noindex цел). Системно зашито в `frontend-dev` (раздел CTA) + урок `failures.md` #cta.
