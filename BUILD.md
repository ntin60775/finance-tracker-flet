# Быстрая инструкция по сборке

## 🚀 Быстрый старт

### Linux (portable)

```bash
pyinstaller finance_tracker_linux.spec --clean --noconfirm
```

Запуск собранной версии:

```bash
dist/finance_tracker/finance_tracker
```

Создание ярлыка на рабочем столе (MX Linux):

```bash
cat > ~/Desktop/FinanceTracker.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Finance Tracker
Exec=/полный/путь/к/папке/dist/finance_tracker/finance_tracker
Icon=/полный/путь/к/папке/assets/icon.png
Terminal=false
Categories=Office;Finance;
EOF
chmod +x ~/Desktop/FinanceTracker.desktop
```

### 1. Проверка готовности
```powershell
.\build_check.ps1
```

### 2. Сборка приложения
```powershell
pyinstaller finance_tracker.spec --clean --noconfirm
```

### 3. Тестирование
```powershell
dist\finance_tracker.exe
```

## 🤖 GitHub Actions: portable-сборки Linux + Windows

- Workflow: `.github/workflows/release-builds.yml`
- Триггеры: ручной запуск (`workflow_dispatch`) и push тега `v*`
- Python в CI: `3.13`
- Артефакты run-а: архивы Linux (`.tar.gz`) и Windows 10/11 (`.zip`) с именами вида:
  - `finance-tracker-vX.Y.Z-linux-x86_64-portable.tar.gz`
  - `finance-tracker-vX.Y.Z-windows-10-11-x86_64-portable.zip`

Скачать архивы можно на странице конкретного запуска GitHub Actions в блоке **Artifacts**.

## 📋 Checklist

**Перед сборкой:**
- [ ] `.\build_check.ps1` проходит без ошибок
- [ ] Все тесты зелёные: `pytest tests/ -v`
- [ ] Приложение запускается: `python -m finance_tracker`

**После сборки:**
- [ ] .exe запускается без ошибок
- [ ] Создаются логи в `dist\.finance_tracker_data\logs\`
- [ ] Процесс остаётся активным (не закрывается сразу)
- [ ] Открывается нативное окно (не браузер)

## 🔧 Если что-то не работает

1. **Приложение сразу закрывается:**
   - Проверьте `view=ft.AppView.FLET_APP` в точках входа
   - См. `.kiro/steering/build-deployment.md`

2. **Ошибки при сборке:**
   - Запустите `.\build_check.ps1` для диагностики
   - Проверьте `finance_tracker.spec`

3. **Отладка с консолью:**
   ```powershell
   # Временно включить консоль в .spec файле
   console=True
   
   # Пересобрать и запустить
   pyinstaller finance_tracker.spec --noconfirm
   dist\finance_tracker.exe
   ```

## 📖 Подробная документация

См. полное руководство: `.kiro/steering/build-deployment.md`
