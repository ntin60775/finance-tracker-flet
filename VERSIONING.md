# VERSIONING

Эта стратегия версионирования применяется для дальнейшей разработки проекта и публикации релизов.

## 1) Политика SemVer (MAJOR.MINOR.PATCH)

- `MAJOR` (`X.0.0`) — несовместимые изменения API/поведения, требующие явной миграции.
- `MINOR` (`0.Y.0`) — новая функциональность без ломки обратной совместимости.
- `PATCH` (`0.0.Z`) — исправления багов и мелкие улучшения без изменения публичного контракта.

Примеры:
- `1.4.2 -> 1.4.3` (фикс)
- `1.4.3 -> 1.5.0` (новая функция)
- `1.5.0 -> 2.0.0` (breaking changes)

## 2) Политика pre-release (`-alpha`, `-beta`, `-rc`)

- `-alpha.N` — ранняя внутренняя/техническая проверка, возможны частые изменения.
- `-beta.N` — функциональность в основном готова, идет стабилизация.
- `-rc.N` — release candidate, кандидат в финальный релиз.

Формат: `X.Y.Z-suffix.N`

Примеры:
- `2.1.0-alpha.1`
- `2.1.0-beta.2`
- `2.1.0-rc.1`

## 3) Конвенция веток и тегов

- Ветки релиза: `release/vX.Y.Z` (например, `release/v2.1.0`).
- Git-тег релиза: `vX.Y.Z` (например, `v2.1.0`).
- Для pre-release использовать тег с суффиксом: `vX.Y.Z-alpha.N`, `vX.Y.Z-beta.N`, `vX.Y.Z-rc.N`.

## 4) Именование артефактов GitHub Releases

Шаблон имени: `finance-tracker-vX.Y.Z-<platform>-portable.<ext>`

- Linux portable:
  - `finance-tracker-v2.1.0-linux-x86_64-portable.tar.gz`
- Windows 10/11 portable:
  - `finance-tracker-v2.1.0-windows-10-11-x86_64-portable.zip`

Для pre-release сохранять тот же шаблон с полной версией:
- `finance-tracker-v2.1.0-rc.1-linux-x86_64-portable.tar.gz`
- `finance-tracker-v2.1.0-rc.1-windows-10-11-x86_64-portable.zip`

## 5) Короткий release checklist (GitHub Releases)

1. Проверить, что версия в релизе соответствует SemVer и стратегии pre-release.
2. Создать/проверить тег формата `vX.Y.Z` (или `vX.Y.Z-suffix.N`).
3. Собрать portable-артефакты для Linux и Windows 10/11.
4. Проверить имена файлов по принятому шаблону.
5. Загрузить оба артефакта в GitHub Release и кратко описать изменения.
