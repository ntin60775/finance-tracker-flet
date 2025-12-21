#!/usr/bin/env python3
"""
Скрипт для проверки использования Flet Dialog API в проекте.

Ищет устаревшие паттерны использования Dialog API:
- page.dialog = ...
- dialog.open = True
- dialog.open = False

И современные паттерны:
- page.open(...)
- page.close(...)

Создаёт отчёт с результатами анализа.
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum
from datetime import datetime


class FileType(Enum):
    """Тип файла."""
    TEST = "test"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class APIType(Enum):
    """Тип используемого API."""
    LEGACY = "legacy"
    MODERN = "modern"
    MIXED = "mixed"
    NONE = "none"


@dataclass
class PatternMatch:
    """Найденный паттерн в коде."""
    line_number: int
    column: int
    pattern_type: str  # "page.dialog", "dialog.open_true", "dialog.open_false", "page.open", "page.close"
    code_snippet: str
    context_before: str = ""
    context_after: str = ""


@dataclass
class FileAnalysisResult:
    """Результат анализа файла."""
    file_path: str
    file_type: FileType
    api_type: APIType
    legacy_patterns: List[PatternMatch]
    modern_patterns: List[PatternMatch]
    requires_migration: bool


class DialogAPIChecker:
    """Проверяет использование Dialog API в файлах."""

    # Паттерны для поиска устаревшего API
    LEGACY_PATTERNS = {
        "page.dialog": re.compile(r'page\.dialog\s*='),
        "dialog.open_true": re.compile(r'(\w+)\.open\s*=\s*True'),
        "dialog.open_false": re.compile(r'(\w+)\.open\s*=\s*False'),
    }

    # Паттерны для поиска современного API
    MODERN_PATTERNS = {
        "page.open": re.compile(r'page\.open\s*\('),
        "page.close": re.compile(r'page\.close\s*\('),
    }

    # Расширения файлов для анализа
    PYTHON_EXTENSIONS = {'.py'}

    # Директории для исключения
    EXCLUDE_DIRS = {
        '.git', '.hypothesis', '.pytest_cache', '.ruff_cache',
        'build', 'dist', 'htmlcov', '__pycache__', '.backup',
        '.kiro', 'node_modules', '.venv', 'venv'
    }

    def __init__(self, project_root: str = "."):
        """Инициализирует проверяющий."""
        self.project_root = Path(project_root)
        self.results: List[FileAnalysisResult] = []

    def determine_file_type(self, file_path: Path) -> FileType:
        """Определяет тип файла (тест или production)."""
        path_str = str(file_path)
        if 'tests' in path_str or 'test_' in file_path.name:
            return FileType.TEST
        elif 'src' in path_str or 'finance_tracker' in path_str:
            return FileType.PRODUCTION
        return FileType.UNKNOWN

    def find_patterns(self, content: str, patterns: Dict[str, re.Pattern]) -> List[PatternMatch]:
        """Находит паттерны в содержимом файла."""
        matches = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern_name, pattern_regex in patterns.items():
                for match in pattern_regex.finditer(line):
                    # Получаем контекст (строки до и после)
                    context_before = lines[line_num - 2] if line_num > 1 else ""
                    context_after = lines[line_num] if line_num < len(lines) else ""

                    matches.append(PatternMatch(
                        line_number=line_num,
                        column=match.start(),
                        pattern_type=pattern_name,
                        code_snippet=line.strip(),
                        context_before=context_before.strip(),
                        context_after=context_after.strip(),
                    ))

        return matches

    def determine_api_type(self, legacy_patterns: List[PatternMatch],
                          modern_patterns: List[PatternMatch]) -> APIType:
        """Определяет тип используемого API."""
        has_legacy = len(legacy_patterns) > 0
        has_modern = len(modern_patterns) > 0

        if has_legacy and has_modern:
            return APIType.MIXED
        elif has_legacy:
            return APIType.LEGACY
        elif has_modern:
            return APIType.MODERN
        else:
            return APIType.NONE

    def analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """Анализирует один файл."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, IOError) as e:
            print(f"⚠️  Ошибка при чтении файла {file_path}: {e}")
            return None

        file_type = self.determine_file_type(file_path)
        legacy_patterns = self.find_patterns(content, self.LEGACY_PATTERNS)
        modern_patterns = self.find_patterns(content, self.MODERN_PATTERNS)
        api_type = self.determine_api_type(legacy_patterns, modern_patterns)

        requires_migration = api_type in (APIType.LEGACY, APIType.MIXED)

        return FileAnalysisResult(
            file_path=str(file_path.relative_to(self.project_root)),
            file_type=file_type,
            api_type=api_type,
            legacy_patterns=legacy_patterns,
            modern_patterns=modern_patterns,
            requires_migration=requires_migration,
        )

    def should_skip_directory(self, dir_path: Path) -> bool:
        """Проверяет, нужно ли пропустить директорию."""
        return dir_path.name in self.EXCLUDE_DIRS

    def scan_project(self) -> List[FileAnalysisResult]:
        """Сканирует весь проект и анализирует файлы."""
        results = []

        for file_path in self.project_root.rglob('*.py'):
            # Пропускаем файлы в исключённых директориях
            if any(part in self.EXCLUDE_DIRS for part in file_path.parts):
                continue

            result = self.analyze_file(file_path)
            if result:
                results.append(result)

        self.results = results
        return results


class ReportGenerator:
    """Генерирует отчёты о результатах анализа."""

    def __init__(self, results: List[FileAnalysisResult]):
        """Инициализирует генератор отчётов."""
        self.results = results

    def generate_summary(self) -> Dict:
        """Генерирует сводку результатов."""
        total_files = len(self.results)
        files_with_legacy = [r for r in self.results if r.api_type in (APIType.LEGACY, APIType.MIXED)]
        files_with_modern = [r for r in self.results if r.api_type in (APIType.MODERN, APIType.MIXED)]
        test_files = [r for r in self.results if r.file_type == FileType.TEST]
        production_files = [r for r in self.results if r.file_type == FileType.PRODUCTION]

        total_legacy_patterns = sum(len(r.legacy_patterns) for r in self.results)
        total_modern_patterns = sum(len(r.modern_patterns) for r in self.results)

        return {
            'total_files': total_files,
            'files_with_legacy_api': len(files_with_legacy),
            'files_with_modern_api': len(files_with_modern),
            'test_files': len(test_files),
            'production_files': len(production_files),
            'total_legacy_patterns': total_legacy_patterns,
            'total_modern_patterns': total_modern_patterns,
            'files_requiring_migration': len([r for r in self.results if r.requires_migration]),
        }

    def print_console_report(self):
        """Выводит отчёт в консоль."""
        summary = self.generate_summary()

        print("\n" + "=" * 80)
        print("📊 ОТЧЁТ О ПРОВЕРКЕ FLET DIALOG API")
        print("=" * 80)

        print(f"\n📈 СВОДКА:")
        print(f"  • Всего файлов проанализировано: {summary['total_files']}")
        print(f"  • Файлов с устаревшим API: {summary['files_with_legacy_api']}")
        print(f"  • Файлов с современным API: {summary['files_with_modern_api']}")
        print(f"  • Файлов требующих миграции: {summary['files_requiring_migration']}")
        print(f"\n  • Тестовых файлов: {summary['test_files']}")
        print(f"  • Production файлов: {summary['production_files']}")
        print(f"\n  • Всего устаревших паттернов: {summary['total_legacy_patterns']}")
        print(f"  • Всего современных паттернов: {summary['total_modern_patterns']}")

        # Файлы требующие миграции
        files_to_migrate = [r for r in self.results if r.requires_migration]
        if files_to_migrate:
            print(f"\n⚠️  ФАЙЛЫ ТРЕБУЮЩИЕ МИГРАЦИИ ({len(files_to_migrate)}):")
            print("-" * 80)

            # Группируем по типу файла
            test_files = [r for r in files_to_migrate if r.file_type == FileType.TEST]
            prod_files = [r for r in files_to_migrate if r.file_type == FileType.PRODUCTION]

            if test_files:
                print(f"\n  📝 ТЕСТОВЫЕ ФАЙЛЫ ({len(test_files)}):")
                for result in sorted(test_files, key=lambda r: r.file_path):
                    self._print_file_details(result)

            if prod_files:
                print(f"\n  🔧 PRODUCTION ФАЙЛЫ ({len(prod_files)}):")
                for result in sorted(prod_files, key=lambda r: r.file_path):
                    self._print_file_details(result)

        # Файлы с современным API
        modern_files = [r for r in self.results if r.api_type == APIType.MODERN]
        if modern_files:
            print(f"\n✅ ФАЙЛЫ С СОВРЕМЕННЫМ API ({len(modern_files)}):")
            print("-" * 80)
            for result in sorted(modern_files, key=lambda r: r.file_path)[:10]:  # Показываем первые 10
                print(f"  ✓ {result.file_path}")
            if len(modern_files) > 10:
                print(f"  ... и ещё {len(modern_files) - 10} файлов")

        print("\n" + "=" * 80)

    def _print_file_details(self, result: FileAnalysisResult):
        """Выводит детали файла."""
        file_type_str = "📝 ТЕСТ" if result.file_type == FileType.TEST else "🔧 PROD"
        print(f"\n  {file_type_str}: {result.file_path}")

        if result.legacy_patterns:
            print(f"    Устаревшие паттерны ({len(result.legacy_patterns)}):")
            for pattern in result.legacy_patterns[:5]:  # Показываем первые 5
                print(f"      • Строка {pattern.line_number}: {pattern.pattern_type}")
                print(f"        Код: {pattern.code_snippet[:70]}")
            if len(result.legacy_patterns) > 5:
                print(f"      ... и ещё {len(result.legacy_patterns) - 5} паттернов")

    def generate_json_report(self, output_file: str = "dialog_api_report.json"):
        """Генерирует JSON отчёт."""
        import json

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.generate_summary(),
            'files': []
        }

        for result in self.results:
            file_data = {
                'file_path': result.file_path,
                'file_type': result.file_type.value,
                'api_type': result.api_type.value,
                'requires_migration': result.requires_migration,
                'legacy_patterns': [
                    {
                        'line_number': p.line_number,
                        'pattern_type': p.pattern_type,
                        'code_snippet': p.code_snippet,
                    }
                    for p in result.legacy_patterns
                ],
                'modern_patterns': [
                    {
                        'line_number': p.line_number,
                        'pattern_type': p.pattern_type,
                        'code_snippet': p.code_snippet,
                    }
                    for p in result.modern_patterns
                ],
            }
            report_data['files'].append(file_data)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 JSON отчёт сохранён в: {output_file}")

    def generate_csv_report(self, output_file: str = "dialog_api_report.csv"):
        """Генерирует CSV отчёт."""
        import csv

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Файл', 'Тип файла', 'Тип API', 'Требует миграции',
                'Устаревших паттернов', 'Современных паттернов'
            ])

            for result in sorted(self.results, key=lambda r: r.file_path):
                writer.writerow([
                    result.file_path,
                    result.file_type.value,
                    result.api_type.value,
                    'Да' if result.requires_migration else 'Нет',
                    len(result.legacy_patterns),
                    len(result.modern_patterns),
                ])

        print(f"💾 CSV отчёт сохранён в: {output_file}")


def main():
    """Главная функция."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Проверяет использование Flet Dialog API в проекте'
    )
    parser.add_argument(
        '--project-root',
        default='.',
        help='Корневая директория проекта (по умолчанию: текущая директория)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Генерировать JSON отчёт'
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Генерировать CSV отчёт'
    )
    parser.add_argument(
        '--output',
        default='dialog_api_report',
        help='Базовое имя для файлов отчётов (по умолчанию: dialog_api_report)'
    )

    args = parser.parse_args()

    # Запускаем проверку
    print("🔍 Сканирование проекта...")
    checker = DialogAPIChecker(args.project_root)
    results = checker.scan_project()

    print(f"✓ Проанализировано {len(results)} файлов")

    # Генерируем отчёты
    generator = ReportGenerator(results)
    generator.print_console_report()

    if args.json:
        generator.generate_json_report(f"{args.output}.json")

    if args.csv:
        generator.generate_csv_report(f"{args.output}.csv")

    # Возвращаем код выхода в зависимости от результатов
    files_requiring_migration = [r for r in results if r.requires_migration]
    if files_requiring_migration:
        print(f"\n⚠️  Найдено {len(files_requiring_migration)} файлов требующих миграции")
        return 1
    else:
        print("\n✅ Все файлы используют современный API!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
