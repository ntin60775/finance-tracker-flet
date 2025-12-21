"""
Точка входа для запуска через python -m finance_tracker
"""
import flet as ft
from finance_tracker.app import main

if __name__ == "__main__":
    # Запуск в режиме нативного десктопного приложения
    # view=ft.AppView.FLET_APP создаёт нативное окно (не веб-браузер)
    ft.app(
        target=main, 
        assets_dir="assets",
        view=ft.AppView.FLET_APP
    )
