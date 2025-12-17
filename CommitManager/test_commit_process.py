#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования процесса создания коммита без GUI
Версия: V3.4.185 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from CommitManager.config_manager import ConfigManager
from CommitManager.project_config import ProjectConfig
from CommitManager.commit_executor import CommitExecutor
from CommitManager.commit_analyzer import CommitAnalyzer
from CommitManager.logger import CommitLogger, LoggingOutputCallback


def test_commit_process():
    """Тестирование процесса создания коммита"""
    
    # Определяем директорию CommitTest
    test_commit_dir = project_root / "CommitTest"
    
    if not test_commit_dir.exists():
        print(f"❌ ОШИБКА: Тестовая директория не найдена: {test_commit_dir}")
        return False
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПРОЦЕССА СОЗДАНИЯ КОММИТА")
    print("=" * 80)
    print(f"Директория: {test_commit_dir}")
    print()
    
    # Создаем конфигурацию для CommitTest
    config_data = {
        'name': 'FSA-Test',
        'path': str(test_commit_dir),
        'version_file': 'Version.txt',
        'version_format': 'V{MAJOR}.{MINOR}.{PATCH}',
        'key_files': ['Version.txt', 'README.md'],
        'binary_files': [],  # В тесте бинарные файлы не пересобираем
        'history': {
            'enabled': True,
            'files': ['clear_cache.py', 'packet_run_gui.py'],
            'directory': 'History',
            'folder_format': '{date}',
            'max_snapshots': 100,
            'auto_cleanup': True,
            'create_on_key_files_change': True
        },
        'versioning': {
            'update_key_files': True,
            'update_release_date': True,
            'file_extensions': ['.py', '.sh', '.md'],
            'version_template': 'Версия проекта: {version}',
            'date_template': 'Дата релиза: {date}'
        },
        'commit': {
            'ask_permission': False,  # В тестовом режиме не спрашиваем
            'show_file_list': True,
            'message_template': 'Проект: {project}\nДата: {date}'
        },
        'ai_analysis': {
            'method': 'hybrid',  # Автоматический анализ
            'provider': 'openai',
            'api_key': '',
            'model': 'gpt-4-turbo-preview',
            'temperature': 0.7,
            'max_tokens': 2000,
            'prompt_template': ''
        }
    }
    
    config = ProjectConfig(config_data)
    
    # Создаем логгер
    logger = CommitLogger(str(test_commit_dir), log_dir=str(test_commit_dir / 'Logs'))
    print(f"📝 Логирование: {logger.get_log_file_path()}")
    print()
    
    # Создаем callback для вывода
    def output_callback(message: str):
        """Вывод сообщений в консоль и в лог"""
        print(message)
    
    logging_callback = LoggingOutputCallback(output_callback, logger)
    
    # Создаем исполнитель и анализатор
    executor = CommitExecutor(
        config,
        logging_callback,
        test_mode=False,  # Реальный режим для полного теста
        full_test_mode=True,
        test_env_dir=str(test_commit_dir)
    )
    analyzer = CommitAnalyzer(config, logging_callback)
    
    print("🚀 Начало выполнения алгоритма создания коммита")
    print("=" * 80)
    print()
    
    # Выполняем шаги
    steps = [
        (0, executor.step_0_check_directory),
        (1, executor.step_1_determine_changed_files),
        (2, executor.step_2_check_real_changes),
        (3, executor.step_3_determine_current_version),
        (4, executor.step_4_determine_new_version),
        (5, executor.step_5_collect_analysis_data),
        (6, lambda: executor.step_6_analyze_changes(analyzer)),
        (7, executor.step_7_save_description),
        (8, executor.step_8_check_message_file),
        # (8.5, executor.step_8_5_pause_for_review),  # Пропускаем паузу в автоматическом тесте
        (9, executor.step_9_update_dates_and_versions),
        (10, executor.step_10_verify_dates),
        (11, executor.step_11_update_key_files_versions),
        (11.5, executor.step_11_5_rebuild_binaries),
        (12, executor.step_12_verify_versions),
        (13, executor.step_13_add_files_to_index),
        # (13.5, executor.step_13_5_pause_before_commit),  # Пропускаем паузу в автоматическом тесте
        (14, executor.step_14_create_commit),
        (15, executor.step_15_verify_commit),
        (16, executor.step_16_cleanup),
        (17, executor.step_17_check_history_needed),
        (18, executor.step_18_create_history),
        (19, executor.step_19_validate_history),
        (20, executor.step_20_final_report)
    ]
    
    success_count = 0
    failed_steps = []
    
    for step_num, step_func in steps:
        print(f"\n{'=' * 80}")
        print(f"ШАГ {step_num}: {step_func.__name__}")
        print('=' * 80)
        
        try:
            success = step_func()
            if success:
                success_count += 1
                print(f"✓ Шаг {step_num} выполнен успешно")
            else:
                failed_steps.append(step_num)
                print(f"❌ Шаг {step_num} завершился с ошибкой")
                # Для пауз продолжаем автоматически
                if step_num in [8.5, 13.5]:
                    print(f"⏭ Пропускаем паузу на шаге {step_num} (автоматический режим)")
                    continue
                else:
                    print("\n⚠️ Остановка процесса из-за ошибки на шаге", step_num)
                    break
        except Exception as e:
            failed_steps.append(step_num)
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА на шаге {step_num}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Закрываем логгер
    logger.close()
    
    # Итоговый отчет
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    print(f"Всего шагов: {len(steps)}")
    print(f"Успешно выполнено: {success_count}")
    print(f"Ошибок: {len(failed_steps)}")
    if failed_steps:
        print(f"Проблемные шаги: {', '.join(map(str, failed_steps))}")
    print(f"\n📝 Лог сохранен: {logger.get_log_file_path()}")
    print("=" * 80)
    
    return len(failed_steps) == 0


if __name__ == "__main__":
    success = test_commit_process()
    sys.exit(0 if success else 1)
