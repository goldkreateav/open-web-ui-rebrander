# Базовая версия для ребрендинга

Исходный код Open WebUI зафиксирован для дальнейших изменений брендинга.

| Поле | Значение |
|------|----------|
| **Репозиторий** | https://github.com/open-webui/open-webui |
| **Ветка** | `main` |
| **Тег релиза** | `v0.8.12` |
| **Коммит (полный SHA)** | `9bd84258d09eefe7bf975878fb0e31a5dadfe0f8` |
| **Кратко** | `9bd84258d` — Merge pull request #23120 from open-webui/dev |

**Дата фиксации (локальный клон):** 2026-03-31

При обновлении с апстрима сравнивайте изменения относительно этого коммита.

---

## Ключевые места для ребрендинга (обзор v0.8.12)

| Область | Пути и заметки |
|--------|----------------|
| **Название в UI** | Стор `$WEBUI_NAME` и связанные строки в [`open-webui/src/routes/+layout.svelte`](open-webui/src/routes/+layout.svelte), [`open-webui/src/routes/auth/+page.svelte`](open-webui/src/routes/auth/+page.svelte), [`open-webui/src/lib/stores`](open-webui/src/lib/stores) — заголовки страниц, уведомления (`• Open WebUI`). |
| **Иконки и PWA** | [`open-webui/src/app.html`](open-webui/src/app.html) — favicon/apple-touch-icon; статика: [`open-webui/static/`](open-webui/static/) (`favicon.png`, `favicon.svg`, `apple-touch-icon.png`, `custom.css`, `loader.js`). |
| **Тема / цвета** | `theme-color` в `app.html`; кастомные темы в [`open-webui/static/themes/`](open-webui/static/themes/); Tailwind в [`open-webui/tailwind.config.js`](open-webui/tailwind.config.js). |
| **Локализация** | Много вхождений «Open WebUI» в [`open-webui/src/lib/i18n/locales/*/translation.json`](open-webui/src/lib/i18n/locales) (английский — база для ключей). |
| **Метаданные пакета** | [`open-webui/package.json`](open-webui/package.json) (`name`, `version`); Python — [`open-webui/pyproject.toml`](open-webui/pyproject.toml). |
| **Бэкенд** | [`open-webui/backend/`](open-webui/backend/) — конфиги, ответы API с именем продукта (при необходимости поиск по строке `Open WebUI`). |

**Лицензирование:** в репозитории есть требования к брендингу Open WebUI — перед публикацией сборки изучите [`open-webui/LICENSE`](open-webui/LICENSE) и [`open-webui/LICENSE_NOTICE`](open-webui/LICENSE_NOTICE).

**Карта точек ребрендинга (UI):** см. [`open-webui/BRANDING_MAP.md`](open-webui/BRANDING_MAP.md).
