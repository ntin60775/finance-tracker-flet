"""
Точка входа для запуска через python -m finance_tracker
"""
import flet as ft
from finance_tracker.app import main

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
