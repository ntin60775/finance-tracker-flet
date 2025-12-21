"""
Скрипт для автоматического обновления тестов на современный Flet Dialog API.
"""
import re
import os
from pathlib import Path


def fix_test_file(file_path):
    """Обновляет тестовый файл для использования современного API."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # 1. Убираем проверку page.close.assert_called() в test_initialization
    # В инициализации close НЕ должен вызываться
    pattern_init = r'(def test_initialization\(self\):.*?)(self\.page\.close\.assert_called\(\))'
    if re.search(pattern_init, content, re.DOTALL):
        content = re.sub(pattern_init, r'\1# Инициализация не вызывает page.close()', content, flags=re.DOTALL)
        changes_made.append("Удалена проверка page.close() в test_initialization")
    
    # 2. Заменяем self.assertTrue(self.modal.dialog.open) в циклах и других местах
    # Используем более точный паттерн для замены в контексте
    pattern_assertTrue = r'self\.assertTrue\(self\.modal\.dialog\.open(?:,\s*f?["\'].*?["\']\s*)?\)'
    if re.search(pattern_assertTrue, content):
        content = re.sub(pattern_assertTrue, 'self.page.open.assert_called()', content)
        changes_made.append("Заменены проверки self.assertTrue(self.modal.dialog.open)")
    
    # 3. Заменяем self.assertIn(self.modal.dialog, self.page.overlay)
    pattern_assertIn = r'self\.assertIn\(self\.modal\.dialog,\s*self\.page\.overlay\)'
    if re.search(pattern_assertIn, content):
        content = re.sub(pattern_assertIn, 'self.page.open.assert_called()', content)
        changes_made.append("Заменены проверки self.assertIn(self.modal.dialog, self.page.overlay)")
    
    # 4. Заменяем self.page.update.assert_called_once() после работы с диалогами
    # Удаляем эти проверки, так как современный API не требует page.update()
    pattern_update = r'\s*self\.page\.update\.assert_called_once\(\)\s*'
    if re.search(pattern_update, content):
        content = re.sub(pattern_update, '\n', content)
        changes_made.append("Удалены проверки page.update.assert_called_once()")
    
    # 5. Заменяем assert modal.dialog.open == False в property тестах
    pattern_assert_false = r'assert\s+modal\.dialog\.open\s*==\s*False'
    if re.search(pattern_assert_false, content):
        content = re.sub(pattern_assert_false, 'mock_page.close.assert_called()', content)
        changes_made.append("Заменены проверки assert modal.dialog.open == False")
    
    # 6. Заменяем assert modal.dialog.open == True в property тестах
    pattern_assert_true = r'assert\s+modal\.dialog\.open\s*==\s*True'
    if re.search(pattern_assert_true, content):
        content = re.sub(pattern_assert_true, 'mock_page.open.assert_called()', content)
        changes_made.append("Заменены проверки assert modal.dialog.open == True")
    
    # Сохраняем только если были изменения
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes_made
    
    return False, []


def main():
    """Основная функция."""
    test_dir = Path('tests')
    
    # Файлы, которые нужно обновить
    test_files = [
        'test_transaction_modal.py',
        'test_lender_modal.py',
        'test_loan_modal.py',
        'test_integration.py',
    ]
    
    print("🔧 Обновление тестов на современный Flet Dialog API...\n")
    
    updated_count = 0
    for test_file in test_files:
        file_path = test_dir / test_file
        if file_path.exists():
            updated, changes = fix_test_file(file_path)
            if updated:
                print(f"✅ {test_file}")
                for change in changes:
                    print(f"   • {change}")
                updated_count += 1
            else:
                print(f"⏭️  {test_file} (без изменений)")
        else:
            print(f"⚠️  {test_file} (не найден)")
    
    print(f"\n📊 Обновлено файлов: {updated_count}/{len(test_files)}")
    print("\n✅ Готово! Запустите тесты для проверки: pytest tests/ -v")


if __name__ == '__main__':
    main()
