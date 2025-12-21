"""
Простой launcher для запуска Finance Tracker из корня проекта.

Этот файл предназначен для удобства разработки и позволяет запускать
приложение командой: python main.py

Рекомендуемые способы запуска:
1. python -m finance_tracker  (рекомендуется)
2. python main.py             (для удобства в режиме разработки)
3. FinanceTracker.exe         (после сборки через PyInstaller)

Все способы запуска эквивалентны и используют одну точку входа.
"""
import flet as ft
from finance_tracker.app import main

if __name__ == "__main__":
    # Запуск приложения через основную точку входа
    # view=ft.AppView.FLET_APP создаёт нативное десктопное окно
    ft.app(
        target=main, 
        assets_dir="assets",
        view=ft.AppView.FLET_APP
    )
