"""
Finance Tracker Flet - десктопное приложение для учёта финансов.

Основной пакет приложения.
"""

from __future__ import annotations


def _apply_flet_compatibility_patches() -> None:
    """Runtime-совместимость проекта с Flet 0.80+ API."""
    try:
        import flet as ft
        from flet.controls.base_control import BaseControl
        from flet.controls.material.button import Button
        from flet.controls.material.elevated_button import ElevatedButton
        from flet.controls.material.filled_button import FilledButton
        from flet.controls.material.outlined_button import OutlinedButton
        from flet.controls.material.text_button import TextButton
    except Exception:
        return

    page_prop = getattr(BaseControl, "page", None)
    if isinstance(page_prop, property) and page_prop.fget:
        def _compat_page_get(self):
            if hasattr(self, "_page"):
                return getattr(self, "_page")
            try:
                return page_prop.fget(self)
            except RuntimeError:
                return None

        def _compat_page_set(self, value):
            setattr(self, "_page", value)

        BaseControl.page = property(_compat_page_get, _compat_page_set, page_prop.fdel, page_prop.__doc__)

    if not hasattr(ft.Page, "open"):
        def _open(self, dialog):
            self.show_dialog(dialog)

        setattr(ft.Page, "open", _open)

    if not hasattr(ft.Page, "close"):
        def _close(self, _dialog=None):
            self.pop_dialog()

        setattr(ft.Page, "close", _close)

    def _button_get_text(self):
        content = getattr(self, "content", None)
        if isinstance(content, str):
            return content
        if hasattr(content, "value"):
            return content.value
        return None

    def _button_set_text(self, value):
        self.content = value

    for cls in (Button, TextButton, ElevatedButton, FilledButton, OutlinedButton):
        if not isinstance(getattr(cls, "text", None), property):
            cls.text = property(_button_get_text, _button_set_text)


_apply_flet_compatibility_patches()

__version__ = "2.0.0"
__author__ = "BarykinME"
__license__ = "AGPL-3.0"
