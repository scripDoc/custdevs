#!/usr/bin/env python3
"""
render_screenshot.py — честный полностраничный захват лендинга для ВИЗУАЛЬНОЙ оценки.

Рецепт НЕ выдуман — поднят из уроков офиса (failures.md, 2026-06-01,
теги #screenshot #visual-eval #playwright; benchmark_coach_vs_ours.md:90):

  1) playwright + chromium (headless). Браузеры playwright стоят в ~/.cache/ms-playwright/.
  2) reduced_motion="reduce" — КРИТИЧНО. Без него reveal-анимации (opacity 0→1 по
     IntersectionObserver) НЕ успевают завершиться к моменту fullPage-кадра → проявленный
     контент попадает в кадр ещё прозрачным → ЛОЖНЫЕ «пустые экраны» и заниженный
     визуальный скор (урок: 28/40 вместо честных 33/40). reduced_motion форсит
     CSS @media (prefers-reduced-motion) → .reveal{opacity:1} без transition.
  3) Прокрутка ВСЕЙ высоты шагами с паузами — триггерит IntersectionObserver scroll-reveal.
     Статический скриншот без скролла оставляет такие секции opacity:0 (пустыми) и даёт
     нечестное сравнение.
  4) scroll-to-top, пауза, затем fullPage screenshot.

Вход:  путь к ЛОКАЛЬНОЙ сборке (папка с index.html) ЛИБО URL (http/https/file).
Выход: PNG (по умолчанию /tmp/shots/<имя>.png — как в уроке, в git НЕ коммитится).

Запуск (playwright стоит под /usr/bin/python, не обязательно под `python3`):
    /usr/bin/python scripts/render_screenshot.py deliverables/<slug>/ [-o out.png]
    /usr/bin/python scripts/render_screenshot.py https://example.vercel.app -o /tmp/shots/x.png

DPR: по умолчанию 2 (резкий текст). На очень длинных страницах DPR=2 упирается в лимит
текстуры chromium — скрипт сам делает fallback на DPR=1.
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse


def resolve_target(arg: str) -> str:
    """Папку сборки → file://.../index.html; файл → file://...; URL → как есть."""
    if arg.startswith(("http://", "https://", "file://")):
        return arg
    p = Path(arg).expanduser().resolve()
    if p.is_dir():
        idx = p / "index.html"
        if not idx.is_file():
            sys.exit(f"[render] в папке нет index.html: {p}")
        return idx.as_uri()
    if p.is_file():
        return p.as_uri()
    sys.exit(f"[render] путь не найден: {arg}")


def default_out(arg: str) -> Path:
    p = Path(arg).expanduser()
    if arg.startswith(("http://", "https://")):
        name = (urlparse(arg).netloc or "page").replace(":", "_")
    elif p.is_dir():
        name = p.resolve().name
    else:
        name = p.stem or "page"
    return Path("/tmp/shots") / f"{name}.png"


# JS: плавный проход по всей высоте (триггерит IntersectionObserver), затем возврат наверх.
_SCROLL_JS = """async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
    const fullH = () => Math.max(
        document.body.scrollHeight, document.documentElement.scrollHeight);
    let y = 0;
    while (y < fullH()) { window.scrollTo(0, y); await sleep(120); y += step; }
    window.scrollTo(0, fullH()); await sleep(300);
    window.scrollTo(0, 0); await sleep(600);
}"""


def capture(url: str, out: Path, width: int, dpr: int, viewport_only: bool) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": width, "height": 900},
                device_scale_factor=dpr,
                reduced_motion="reduce",  # см. шапку: гасит фантомные пустоты
            )
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.evaluate(_SCROLL_JS)          # скролл всей высоты → reveal-секции проявлены
            page.wait_for_timeout(400)
            page.screenshot(path=str(out), full_page=not viewport_only)
        finally:
            browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Честный полностраничный захват лендинга (playwright, scroll, reduced-motion).")
    ap.add_argument("target", help="папка сборки (с index.html) или URL")
    ap.add_argument("-o", "--out", help="путь к выходному PNG (по умолч. /tmp/shots/<имя>.png)")
    ap.add_argument("--width", type=int, default=1440, help="ширина вьюпорта (default 1440)")
    ap.add_argument("--dpr", type=int, default=2,
                    help="device scale factor (default 2; на длинных страницах fallback на 1)")
    ap.add_argument("--viewport-only", action="store_true",
                    help="снять только первый экран, без fullPage")
    args = ap.parse_args()

    try:
        import playwright  # noqa: F401
    except ImportError:
        sys.exit("[render] нет python-playwright. Он установлен под /usr/bin/python "
                 "(playwright 1.58, ~/.local/lib/python3.14/site-packages). "
                 "Запускай скрипт через: /usr/bin/python scripts/render_screenshot.py ...")

    url = resolve_target(args.target)
    out = Path(args.out).expanduser() if args.out else default_out(args.target)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        capture(url, out, args.width, args.dpr, args.viewport_only)
    except Exception as e:  # noqa: BLE001 — широкий catch ради fallback на DPR=1
        if args.dpr > 1:
            print(f"[render] DPR={args.dpr} не удалось ({type(e).__name__}: {e}); "
                  f"повтор на DPR=1 (вероятно лимит текстуры длинной страницы).", file=sys.stderr)
            capture(url, out, args.width, 1, args.viewport_only)
        else:
            raise

    if not out.is_file() or out.stat().st_size == 0:
        sys.exit(f"[render] PNG не создан или пуст: {out}")
    print(f"[render] OK → {out} ({out.stat().st_size // 1024} KB) [{url}]", file=sys.stderr)
    print(out)  # stdout = только путь, удобно подхватывать в пайплайне


if __name__ == "__main__":
    main()
