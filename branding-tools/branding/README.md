# Branding applier (Open WebUI)

Этот скрипт применяет детерминированные правки ребрендинга в исходники Open WebUI на основе `branding.config.json`.

Он вносит правки **in-place**:
- меняет `WEBUI_NAME`/`APP_NAME`,
- обновляет `theme-color` и PWA-темы,
- копирует ассеты (favicon/splash/logo/manifest icons) в backend статические файлы,
- обновляет тексты бренда в UI и `src/lib/i18n/locales/**/translation.json`,
- делает backup изменённых файлов и пишет `open-webui/branding-report.md`.

## Запуск

Пример dry-run (ничего не меняет):

```bash
python open-webui/branding/apply_branding.py --config open-webui/branding/branding.config.json.example --dry-run
```

Применение:

```bash
python open-webui/branding/apply_branding.py --config open-webui/branding/branding.config.json
```

## Что ожидается в `branding.config.json`

См. схему:
- [`branding.config.schema.json`](branding.config.schema.json)

И пример:
- [`branding.config.json.example`](branding.config.json.example)

## Backup и отчёт

Backup создаётся в:
- `open-webui/.branding-backups/<timestamp>/...`

Отчёт по операции создаётся в:
- `open-webui/branding-report.md`

