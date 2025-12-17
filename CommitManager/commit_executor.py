#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исполнитель алгоритма создания коммитов
Версия: V3.4.186 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import subprocess
import re
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Callable, Tuple
from .project_config import ProjectConfig


class CommitExecutor:
    """Класс для выполнения алгоритма создания коммитов"""
    
    def __init__(self, config: ProjectConfig, output_callback: Optional[Callable[[str], None]] = None, test_mode: bool = False, full_test_mode: bool = False, test_env_dir: Optional[str] = None):
        """
        Инициализация исполнителя
        
        Args:
            config: Конфигурация проекта
            output_callback: Функция для вывода сообщений (принимает строку)
            test_mode: Режим тестирования (dry-run) - не выполняет реальные действия
            full_test_mode: Полный тестовый режим - работает в временной директории
            test_env_dir: Путь к временной тестовой директории (если full_test_mode=True)
        """
        self.config = config
        self.output_callback = output_callback or print
        self.test_mode = test_mode
        self.full_test_mode = full_test_mode
        self.test_env_dir = test_env_dir
        self.is_paused = False  # Флаг паузы для ожидания подтверждения пользователя
        
        # Если полный тестовый режим, используем временную директорию
        if self.full_test_mode and self.test_env_dir:
            self.project_dir = self.test_env_dir
            # Обновляем конфигурацию для работы с временной директорией
            config.path = self.test_env_dir
        else:
            self.project_dir = config.path
        
        self.vars_file = os.path.join(self.project_dir, '.commit_vars.sh')
        self.analysis_data_file = os.path.join(self.project_dir, '.commit_analysis_data.txt')
        self.commit_message_file = os.path.join(self.project_dir, 'commit_message.txt')
        
        # Переменные состояния
        self.changed_files = []
        self.new_files = []
        self.new_dirs = []
        self.deleted_files = []
        self.current_version = ""
        self.new_version = ""
        self.all_versions = []
        self.current_step = 0
        self.is_paused = False
        self.is_stopped = False
        
        if self.full_test_mode:
            self._output("🧪 ПОЛНЫЙ ТЕСТОВЫЙ РЕЖИМ ВКЛЮЧЕН")
            self._output(f"🧪 Работа в временной директории: {self.project_dir}")
            self._output("🧪 Все операции выполняются в тестовой среде")
            self._output("=" * 60)
        elif self.test_mode:
            self._output("🧪 ТЕСТОВЫЙ РЕЖИМ ВКЛЮЧЕН - реальные действия не выполняются")
            self._output("=" * 60)
    
    def _output(self, message: str):
        """Вывод сообщения через callback"""
        self.output_callback(message)
    
    def _run_command(self, command: List[str], cwd: Optional[str] = None, capture_output: bool = True, simulate_output: Optional[str] = None) -> Tuple[int, str]:
        """
        Выполнить команду
        
        Args:
            command: Список аргументов команды
            cwd: Рабочая директория
            capture_output: Захватывать ли вывод
            simulate_output: Симулированный вывод для тестового режима
        
        Returns:
            (exit_code, output)
        """
        if cwd is None:
            cwd = self.project_dir
        
        # Формируем строку команды для вывода
        cmd_str = ' '.join(command)
        
        if self.test_mode:
            # В тестовом режиме только выводим команду
            self._output(f"🧪 [ТЕСТ] Команда: {cmd_str}")
            if cwd:
                self._output(f"🧪 [ТЕСТ] Рабочая директория: {cwd}")
            
            # Для некоторых команд симулируем вывод
            if simulate_output is not None:
                self._output(f"🧪 [ТЕСТ] Симулированный вывод:\n{simulate_output}")
                return 0, simulate_output
            
            # Для git команд симулируем типичный вывод
            if command[0] == 'git':
                if 'diff' in command or 'status' in command or 'log' in command:
                    # Симулируем вывод git команд
                    if '--name-only' in command:
                        sim_output = '\n'.join(self.changed_files[:5]) if self.changed_files else ''
                    elif '--stat' in command:
                        sim_output = ' file1.py | 10 +++++-----\n file2.py |  5 +++++'
                    elif '--format=%H' in command:
                        sim_output = 'abc123def4567890abcdef1234567890abcdef12'
                    elif '--format=%s' in command:
                        sim_output = '[Тестовый коммит] Изменения в тестовом режиме'
                    elif '--count' in command:
                        sim_output = '42'
                    else:
                        sim_output = 'simulated git output'
                    self._output(f"🧪 [ТЕСТ] Симулированный вывод:\n{sim_output}")
                    return 0, sim_output
            
            # Для других команд возвращаем успех
            return 0, ""
        
        # Реальный режим - выполняем команду
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                encoding='utf-8'
            )
            output = result.stdout if capture_output else ""
            return result.returncode, output
        except Exception as e:
            self._output(f"❌ Ошибка выполнения команды: {e}")
            return 1, str(e)
    
    def _save_vars_to_file(self):
        """Сохранить переменные в файл .commit_vars.sh"""
        try:
            with open(self.vars_file, 'w', encoding='utf-8') as f:
                f.write("# Переменные для продолжения создания коммита\n")
                f.write("# Этот файл будет удален после завершения процесса\n\n")
                f.write(f'CHANGED_FILES="{" ".join(self.changed_files)}"\n')
                f.write(f'NEW_FILES="{" ".join(self.new_files)}"\n')
                f.write(f'NEW_DIRS="{" ".join(self.new_dirs)}"\n')
                f.write(f'DELETED_FILES="{" ".join(self.deleted_files)}"\n')
                f.write(f'CURRENT_VERSION="{self.current_version}"\n')
                f.write(f'NEW_VERSION="{self.new_version}"\n')
                f.write(f'ALL_VERSIONS="{" ".join(self.all_versions)}"\n')
        except Exception as e:
            self._output(f"⚠️ Предупреждение: Не удалось сохранить переменные: {e}")
    
    def step_0_check_directory(self) -> bool:
        """ШАГ 0: Проверка директории"""
        self.current_step = 0
        self._output("=== ШАГ 0: Проверка директории ===")
        
        if self.test_mode:
            self._output("")
            self._output("🧪" + "=" * 58)
            self._output("🧪 ТЕСТОВЫЙ РЕЖИМ АКТИВЕН")
            self._output("🧪 Все команды будут выведены, но НЕ выполнены")
            self._output("🧪 Файлы проекта НЕ будут изменены")
            self._output("🧪 Коммит НЕ будет создан")
            self._output("🧪" + "=" * 58)
            self._output("")
        
        # Проверяем текущую директорию
        exit_code, output = self._run_command(['pwd'])
        if exit_code != 0:
            self._output("❌ ОШИБКА: Не удалось определить текущую директорию")
            return False
        
        current_dir = output.strip()
        expected_dir = self.project_dir
        
        # Если мы не в нужной директории, переходим
        if current_dir != expected_dir:
            if not os.path.exists(expected_dir):
                self._output(f"❌ ОШИБКА: Директория проекта не существует: {expected_dir}")
                return False
            
            os.chdir(expected_dir)
            self._output(f"✓ Переход в директорию проекта: {expected_dir}")
        else:
            self._output(f"✓ Рабочая директория: {current_dir}")
        
        # Дополнительная проверка
        if not os.path.exists(os.path.join(expected_dir, '.git')):
            self._output("⚠️ Предупреждение: Директория не является git репозиторием")
        
        return True
    
    def step_1_determine_changed_files(self) -> bool:
        """ШАГ 1: Определение измененных файлов"""
        self.current_step = 1
        self._output("=== ШАГ 1: Определение измененных файлов ===")
        
        # Измененные файлы
        exit_code, output = self._run_command(['git', 'diff', '--name-only', 'HEAD'])
        if exit_code == 0:
            self.changed_files = [f.strip() for f in output.strip().split('\n') if f.strip()]
        
        # Новые файлы и директории
        exit_code, output = self._run_command(['git', 'status', '--short'])
        if exit_code == 0:
            new_items = []
            for line in output.strip().split('\n'):
                if line.startswith('??'):
                    item = line[3:].strip()
                    if item:
                        new_items.append(item)
            
            # Разделяем на файлы и директории
            for item in new_items:
                full_path = os.path.join(self.project_dir, item)
                if os.path.isdir(full_path):
                    self.new_dirs.append(item)
                elif os.path.isfile(full_path):
                    self.new_files.append(item)
        
        # Удаленные файлы
        exit_code, output = self._run_command(['git', 'diff', '--name-only', '--diff-filter=D', 'HEAD'])
        if exit_code == 0:
            self.deleted_files = [f.strip() for f in output.strip().split('\n') if f.strip()]
        
        # Проверка наличия изменений
        if not self.changed_files and not self.new_files and not self.new_dirs and not self.deleted_files:
            self._output("❌ ОШИБКА: Нет изменений для коммита")
            return False
        
        self._output(f"Измененные файлы: {len(self.changed_files)}")
        self._output(f"Новые файлы: {len(self.new_files)}")
        self._output(f"Новые директории: {len(self.new_dirs)}")
        self._output(f"Удаленные файлы: {len(self.deleted_files)}")
        
        # Сохраняем переменные
        self._save_vars_to_file()
        self._output("✓ Переменные шага 1 сохранены в .commit_vars.sh")
        
        return True
    
    def step_2_check_real_changes(self) -> bool:
        """ШАГ 2: Проверка реальных изменений (внутренняя)"""
        self.current_step = 2
        # Пользователь НЕ видит этот вывод согласно правилам
        
        has_real_changes = False
        
        for file in self.changed_files:
            if not file:
                continue
            
            exit_code, output = self._run_command(['git', 'diff', 'HEAD', file])
            if exit_code == 0:
                # Фильтруем строки с версиями/датами
                lines = output.split('\n')
                filtered_lines = [
                    line for line in lines
                    if line.startswith('+') or line.startswith('-')
                    if not re.search(r'Версия|Version|дата|Date', line, re.IGNORECASE)
                ]
                
                if filtered_lines:
                    has_real_changes = True
                    break
        
        if not has_real_changes:
            self._output("❌ ОШИБКА: Нет реальных изменений кода, только версии/даты")
            return False
        
        return True
    
    def step_3_determine_current_version(self) -> bool:
        """ШАГ 3: Определение текущей версии"""
        self.current_step = 3
        self._output("=== ШАГ 3: Определение текущей версии ===")

        all_files_to_check = self.changed_files + self.new_files
        versions_found = set()

        # Всегда проверяем файл версии, даже если он не изменен
        version_file_path = self.config.get_version_file_path()
        if os.path.exists(version_file_path):
            # Читаем APP_VERSION из Version.txt
            try:
                with open(version_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('APP_VERSION='):
                            version_str = line.split('=', 1)[1].strip()
                            # Извлекаем версию формата VX.Y.Z
                            match = re.search(r'V(\d+)\.(\d+)\.(\d+)', version_str)
                            if match:
                                version = f"V{match.group(1)}.{match.group(2)}.{match.group(3)}"
                                versions_found.add(version)
                                self._output(f"✓ Найдена версия в {os.path.basename(version_file_path)}: {version}")
            except Exception as e:
                self._output(f"⚠️ Предупреждение: Не удалось прочитать версию из {version_file_path}: {e}")

        # Также проверяем измененные и новые файлы
        for file in all_files_to_check:
            if not file:
                continue

            # Пропускаем файл версии, если он уже проверен
            if file == self.config.version_file or file.endswith('Version.txt'):
                continue

            # Проверяем расширение файла
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.config.file_extensions:
                continue

            full_path = os.path.join(self.project_dir, file)
            if not os.path.isfile(full_path):
                continue

            # Читаем первые 20 строк и ищем версию
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:20]
                    content = ''.join(lines)
                    
                    # Ищем версии формата VX.Y.Z
                    matches = re.findall(r'V(\d+)\.(\d+)\.(\d+)', content)
                    for match in matches:
                        version = f"V{match[0]}.{match[1]}.{match[2]}"
                        versions_found.add(version)
            except Exception:
                continue
        
        self.all_versions = sorted(list(versions_found))
        
        if self.all_versions:
            self.current_version = self.all_versions[0]
        else:
            self._output("❌ ОШИБКА: Не удалось найти версию в измененных или новых файлах проекта")
            self._output(f"   Проверены файлы: {', '.join(all_files_to_check[:5])}")
            return False
        
        self._output(f"Найдены версии в файлах: {' '.join(self.all_versions)}")
        self._output(f"Основная версия для замены: {self.current_version}")
        
        # Сохраняем переменные
        self._save_vars_to_file()
        self._output("✓ Переменные шага 3 сохранены в .commit_vars.sh")
        
        return True
    
    def step_4_determine_new_version(self) -> bool:
        """ШАГ 4: Определение новой версии"""
        self.current_step = 4
        self._output("=== ШАГ 4: Определение новой версии ===")
        
        version_file_path = self.config.get_version_file_path()
        if not os.path.exists(version_file_path):
            self._output(f"❌ ОШИБКА: Файл версии не найден: {version_file_path}")
            return False
        
        # Читаем MAJOR и MINOR из файла версии
        major = None
        minor = None
        
        try:
            with open(version_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('MAJOR='):
                        major = line.split('=', 1)[1].strip()
                    elif line.startswith('MINOR='):
                        minor = line.split('=', 1)[1].strip()
        except Exception as e:
            self._output(f"❌ ОШИБКА: Не удалось прочитать файл версии: {e}")
            return False
        
        if not major or not minor:
            self._output("❌ ОШИБКА: Не удалось прочитать MAJOR или MINOR из файла версии")
            return False
        
        # Определяем текущий номер коммита
        exit_code, output = self._run_command(['git', 'rev-list', '--count', 'HEAD'])
        if exit_code != 0:
            self._output("❌ ОШИБКА: Не удалось определить количество коммитов")
            return False
        
        try:
            current_commit = int(output.strip())
            new_patch = current_commit + 1
        except ValueError:
            self._output("❌ ОШИБКА: Неверный формат количества коммитов")
            return False
        
        # Формируем новую версию
        self.new_version = f"V{major}.{minor}.{new_patch}"
        
        if not self.new_version or self.new_version == "V..":
            self._output(f"❌ ОШИБКА: Не удалось сформировать новую версию: {self.new_version}")
            return False
        
        self._output(f"Новая версия: {self.new_version} (текущая: {self.current_version})")
        
        # Сохраняем переменные
        self._save_vars_to_file()
        self._output("✓ Переменные шага 4 сохранены в .commit_vars.sh")
        
        return True
    
    def step_5_collect_analysis_data(self) -> bool:
        """ШАГ 5: Сбор подробной информации об изменениях"""
        self.current_step = 5
        self._output("=== ШАГ 5: Сбор подробной информации об изменениях ===")
        self._output("=== Сбор данных для анализа... ===")
        
        try:
            with open(self.analysis_data_file, 'w', encoding='utf-8') as f:
                # Обрабатываем измененные файлы
                for file in self.changed_files:
                    if not file:
                        continue
                    
                    f.write(f"=== Файл: {file} ===\n")
                    
                    # Статистика изменений
                    exit_code, output = self._run_command(['git', 'diff', '--stat', 'HEAD', file])
                    if exit_code == 0 and output:
                        stat_line = output.strip().split('\n')[-1] if output.strip() else ""
                        f.write(f"Статистика: {stat_line}\n")
                    
                    # Изменения (без версий/дат)
                    exit_code, output = self._run_command(['git', 'diff', 'HEAD', file])
                    if exit_code == 0:
                        lines = output.split('\n')
                        filtered_lines = [
                            line for line in lines
                            if (line.startswith('+') or line.startswith('-'))
                            and not line.startswith('+++') and not line.startswith('---')
                            and not re.search(r'Версия|Version|дата|Date', line, re.IGNORECASE)
                        ][:100]
                        
                        if filtered_lines:
                            f.write("Изменения:\n")
                            f.write('\n'.join(filtered_lines))
                            f.write("\n")
                    
                    f.write("\n")
                
                # Обрабатываем новые файлы
                for file in self.new_files:
                    if not file:
                        continue
                    
                    full_path = os.path.join(self.project_dir, file)
                    if not os.path.isfile(full_path):
                        continue
                    
                    f.write(f"=== Файл: {file} (новый) ===\n")
                    
                    # Количество строк
                    try:
                        with open(full_path, 'r', encoding='utf-8') as file_obj:
                            line_count = sum(1 for _ in file_obj)
                        f.write(f"Статистика: новый файл, строк: {line_count}\n")
                    except Exception:
                        f.write("Статистика: новый файл\n")
                    
                    # Содержимое (первые 100 строк, без версий/дат)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as file_obj:
                            lines = file_obj.readlines()[:100]
                            filtered_lines = [
                                line for line in lines
                                if not re.search(r'Версия|Version|дата|Date', line, re.IGNORECASE)
                            ]
                            
                            if filtered_lines:
                                f.write("Содержимое (первые 100 строк):\n")
                                f.write(''.join(filtered_lines))
                    except Exception:
                        pass
                    
                    f.write("\n---\n\n")
            
            self._output("=== Ассистент анализирует изменения и формирует описание коммита... ===")
            
            if self.test_mode:
                self._output("🧪 [ТЕСТ] Файл с данными анализа создан (симулированно)")
                self._output("🧪 [ТЕСТ] В тестовом режиме анализ будет выполнен, но файлы не изменятся")
            
            self._output("⏸ ПАУЗА: Ассистент должен остановиться здесь")
            
            return True
        except Exception as e:
            self._output(f"❌ ОШИБКА: Не удалось собрать данные для анализа: {e}")
            return False
    
    def step_6_analyze_changes(self, analyzer) -> bool:
        """ШАГ 6: Анализ изменений ассистентом"""
        self.current_step = 6
        self._output("=== ШАГ 6: Анализ изменений ===")
        
        # Анализ выполняется через CommitAnalyzer
        # Этот шаг просто вызывает анализатор
        if analyzer.analyze_changes():
            self._output("✓ Анализ изменений завершен")
            return True
        else:
            self._output("❌ ОШИБКА: Не удалось проанализировать изменения")
            return False
    
    def step_7_save_description(self) -> bool:
        """ШАГ 7: Сохранение описания (выполняется анализатором)"""
        self.current_step = 7
        # Этот шаг выполняется в CommitAnalyzer
        return True
    
    def step_8_check_message_file(self) -> bool:
        """ШАГ 8: Проверка файла сообщения"""
        self.current_step = 8
        self._output("=== ШАГ 8: Проверка файла сообщения коммита ===")
        
        if self.test_mode:
            # В тестовом режиме создаем симулированный файл сообщения
            if not os.path.exists(self.commit_message_file):
                try:
                    test_message = f"""[Тестовый коммит - изменения в тестовом режиме]

Кратко, что изменили (списком):

Тестовый_файл.py:
- Тестовое изменение 1
- Тестовое изменение 2

Проект: {self.config.name}
Дата: {datetime.now().strftime('%Y.%m.%d')}"""
                    with open(self.commit_message_file, 'w', encoding='utf-8') as f:
                        f.write(test_message)
                    self._output("🧪 [ТЕСТ] Создан тестовый файл commit_message.txt")
                except Exception as e:
                    self._output(f"⚠ Предупреждение: Не удалось создать тестовый файл: {e}")
        
        if not os.path.exists(self.commit_message_file):
            self._output("❌ ОШИБКА: Файл commit_message.txt не найден")
            return False
        
        if not os.path.getsize(self.commit_message_file) > 0:
            self._output("❌ ОШИБКА: Файл commit_message.txt пуст")
            return False
        
        if self.test_mode:
            self._output("🧪 [ТЕСТ] Файл commit_message.txt готов (тестовый)")
        else:
            self._output("✓ Файл commit_message.txt готов для коммита")
        return True
    
    def step_8_5_pause_for_review(self) -> bool:
        """ШАГ 8.5: ОБЯЗАТЕЛЬНАЯ ПАУЗА для просмотра и редактирования"""
        self.current_step = 8.5
        self._output("=== ШАГ 8.5: Ожидание разрешения на продолжение ===")
        self._output("")
        self._output("=== Описание коммита готово ===")
        self._output("")
        
        # Показываем содержимое файла
        try:
            with open(self.commit_message_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self._output("Содержимое файла commit_message.txt:")
                self._output("----------------------------------------")
                self._output(content)
                self._output("----------------------------------------")
        except Exception as e:
            self._output(f"⚠️ Предупреждение: Не удалось прочитать файл: {e}")
        
        # Обновляем переменные
        self._save_vars_to_file()
        self._output("✓ Переменные проверены и обновлены в .commit_vars.sh")
        self._output("")
        self._output("🚨 КРИТИЧНО: ОБЯЗАТЕЛЬНАЯ ПАУЗА ДЛЯ АССИСТЕНТА 🚨")
        self._output("⏸ ПАУЗА: Ожидание разрешения пользователя")
        
        # Устанавливаем флаг паузы
        self.is_paused = True
        
        return True
    
    def step_9_update_dates_and_versions(self) -> bool:
        """ШАГ 9: Обновление дат релиза и версий в измененных файлах"""
        self.current_step = 9
        self._output("=== ШАГ 9: Обновление дат релиза и версий в измененных файлах ===")
        
        # Проверяем наличие файла сообщения
        if not os.path.exists(self.commit_message_file):
            self._output("❌ ОШИБКА: Файл commit_message.txt не найден")
            return False
        
        today = datetime.now().strftime('%Y.%m.%d')
        
        # Обновляем даты и версии в измененных файлах
        for file in self.changed_files:
            if not file:
                continue
            
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.config.file_extensions:
                continue
            
            full_path = os.path.join(self.project_dir, file)
            if not os.path.isfile(full_path):
                continue
            
            self._output(f"Обновляем дату релиза в: {file}")
            
            # Обновление дат через sed (для macOS нужен пустой аргумент после -i)
            # Используем Python для кроссплатформенности
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_lines = f.readlines()
                    lines = old_lines.copy()
                
                # Обновляем только первые 20 строк
                updated = False
                for i in range(min(20, len(lines))):
                    # Обновляем даты в формате (YYYY.MM.DD)
                    old_line = lines[i]
                    new_line = re.sub(
                        r'\((\d{4}\.\d{2}\.\d{2})\)',
                        f'({today})',
                        old_line
                    )
                    
                    # Обновляем версию если есть
                    if self.new_version and re.search(r'V\d+\.\d+\.\d+', new_line):
                        new_line = re.sub(
                            r'V\d+\.\d+\.\d+',
                            self.new_version,
                            new_line
                        )
                    
                    if new_line != old_line:
                        lines[i] = new_line
                        updated = True
                
                if updated:
                    if self.test_mode:
                        self._output(f"🧪 [ТЕСТ] БЫЛО БЫ обновлено в: {file}")
                        self._output(f"🧪 [ТЕСТ] Изменения (первые 20 строк):")
                        for i in range(min(20, len(lines))):
                            if i < len(old_lines) and old_lines[i] != lines[i]:
                                self._output(f"🧪 [ТЕСТ]   Строка {i+1}:")
                                self._output(f"🧪 [ТЕСТ]     Было: {old_lines[i].rstrip()}")
                                self._output(f"🧪 [ТЕСТ]     Стало: {lines[i].rstrip()}")
                    else:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        self._output(f"  ✓ Обновлено в: {file}")
            except Exception as e:
                self._output(f"  ⚠️ Предупреждение: Не удалось обновить {file}: {e}")
        
        return True
    
    def step_10_verify_dates(self) -> bool:
        """ШАГ 10: Проверка обновления дат"""
        self.current_step = 10
        self._output("=== ШАГ 10: Проверка обновления дат релиза ===")
        
        today = datetime.now().strftime('%Y.%m.%d')
        errors = []
        
        for file in self.changed_files:
            if not file:
                continue
            
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.config.file_extensions:
                continue
            
            full_path = os.path.join(self.project_dir, file)
            if not os.path.isfile(full_path):
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:20]
                    content = ''.join(lines)
                    
                    # Проверяем, была ли дата в файле изначально (любая дата в формате YYYY.MM.DD)
                    has_date_pattern = bool(re.search(r'\(\d{4}\.\d{2}\.\d{2}\)', content))
                    
                    if has_date_pattern:
                        # Если дата была, проверяем что она обновлена
                        if f"({today})" not in content:
                            errors.append(file)
                        else:
                            self._output(f"✓ Дата обновлена в {file}")
                    else:
                        # Если даты не было изначально, пропускаем проверку
                        self._output(f"ℹ Файл {file} не содержит дату в формате (YYYY.MM.DD) - пропускаем проверку")
            except Exception:
                errors.append(file)
        
        if errors:
            self._output(f"❌ ОШИБКА: Дата релиза не была обновлена в {len(errors)} файл(ах): {', '.join(errors)}")
            return False
        
        self._output("✓ Все даты релиза успешно обновлены")
        return True
    
    def step_11_update_key_files_versions(self) -> bool:
        """ШАГ 11: Обновление версий проекта в ключевых файлах"""
        self.current_step = 11
        self._output("=== ШАГ 11: Обновление версий проекта в ключевых файлах ===")
        
        if not self.new_version:
            self._output("❌ ОШИБКА: NEW_VERSION не определена")
            return False
        
        self._output(f"Обновление версий на: {self.new_version}")
        
        # Обновляем версии в ключевых файлах
        for file in self.config.key_files:
            full_path = os.path.join(self.project_dir, file)
            if not os.path.isfile(full_path):
                self._output(f"⚠ ПРЕДУПРЕЖДЕНИЕ: Файл {file} не найден, пропускаем")
                continue
            
            ext = os.path.splitext(file)[1].lower()
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_lines = f.readlines()
                    lines = old_lines.copy()
                
                updated = False
                
                # Для .py и .md файлов обновляем версию в первых 20 строках
                if ext in ['.py', '.md']:
                    for i in range(min(20, len(lines))):
                        if re.search(r'V\d+\.\d+\.\d+', lines[i]):
                            lines[i] = re.sub(r'V\d+\.\d+\.\d+', self.new_version, lines[i])
                            updated = True
                
                # Для Version.txt обновляем APP_VERSION
                elif file == 'Version.txt' or file.endswith('Version.txt'):
                    for i in range(len(lines)):
                        if lines[i].startswith('APP_VERSION='):
                            lines[i] = f'APP_VERSION={self.new_version}\n'
                            updated = True
                            break
                    else:
                        # Добавляем APP_VERSION если его нет
                        lines.append(f'APP_VERSION={self.new_version}\n')
                        updated = True
                
                if updated:
                    if self.test_mode:
                        self._output(f"🧪 [ТЕСТ] БЫЛО БЫ обновлена версия в: {file}")
                        self._output(f"🧪 [ТЕСТ] Новая версия: {self.new_version}")
                        # Показываем изменения
                        for i in range(min(20, len(lines))):
                            if i < len(old_lines) and old_lines[i] != lines[i]:
                                self._output(f"🧪 [ТЕСТ]   Строка {i+1}:")
                                self._output(f"🧪 [ТЕСТ]     Было: {old_lines[i].rstrip()}")
                                self._output(f"🧪 [ТЕСТ]     Стало: {lines[i].rstrip()}")
                    else:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        self._output(f"  ✓ Версия обновлена в {file}")
                else:
                    self._output(f"  ℹ Файл {file} не содержит версию в начале (пропускаем)")
                    
            except Exception as e:
                self._output(f"  ⚠ Предупреждение: Не удалось обновить {file}: {e}")
        
        return True
    
    def step_11_5_rebuild_binaries(self) -> bool:
        """ШАГ 11.5: Пересборка бинарных файлов"""
        self.current_step = 11.5
        self._output("=== ШАГ 11.5: Пересборка бинарных файлов ===")
        
        # В полном тестовом режиме используем упрощенную сборку
        if self.full_test_mode:
            self._output("🧪 ТЕСТОВЫЙ РЕЖИМ: Использование упрощенной сборки бинарных файлов")
            self._output("")
            
            # Ищем скрипт для создания тестовых бинарников
            test_build_script = os.path.join(self.project_dir, 'test_build_binaries.py')
            if os.path.exists(test_build_script):
                self._output(f"✓ Найден скрипт для тестовой сборки: {os.path.basename(test_build_script)}")
                self._output("Запуск тестовой сборки...")
                
                exit_code, output = self._run_command(['python3', test_build_script], capture_output=False)
                
                if exit_code != 0:
                    self._output(f"⚠️ Предупреждение: Тестовая сборка завершилась с кодом {exit_code}")
                    self._output("Продолжаем без бинарных файлов (тестовый режим)")
                    return True
                
                # Проверяем наличие файлов
                binaries_created = 0
                for binary in self.config.binary_files:
                    if not binary.get('auto_rebuild', False):
                        continue
                    binary_name = binary.get('name', '')
                    binary_path = os.path.join(self.project_dir, binary_name)
                    
                    if os.path.exists(binary_path) and os.path.getsize(binary_path) > 0:
                        self._output(f"✓ Бинарный файл создан: {binary_name}")
                        binaries_created += 1
                
                if binaries_created > 0:
                    self._output(f"✓ Создано бинарных файлов: {binaries_created}/{len([b for b in self.config.binary_files if b.get('auto_rebuild', False)])}")
                    self._output("✓ Бинарные файлы успешно пересобраны (тестовый режим)")
                    return True
                else:
                    self._output("⚠️ Предупреждение: Бинарные файлы не созданы, но продолжаем (тестовый режим)")
                    return True
            else:
                self._output("ℹ Скрипт тестовой сборки не найден, пропускаем пересборку (тестовый режим)")
                return True
        
        # Обычный режим
        self._output("⚠️ ВНИМАНИЕ: Начинается пересборка бинарных файлов.")
        self._output("Это может занять несколько минут. Пожалуйста, подождите...")
        self._output("")
        
        # Удаляем старые бинарники
        for binary in self.config.binary_files:
            if not binary.get('auto_rebuild', False):
                continue
            
            binary_name = binary.get('name', '')
            binary_path = os.path.join(self.project_dir, binary_name)
            if os.path.exists(binary_path):
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ удален: {binary_name}")
                else:
                    try:
                        os.remove(binary_path)
                        self._output(f"✓ Удален старый бинарный файл: {binary_name}")
                    except Exception as e:
                        self._output(f"⚠ Предупреждение: Не удалось удалить {binary_name}: {e}")
        
        # Запускаем сборку (берем команду из первого бинарного файла)
        if self.config.binary_files:
            build_command = self.config.binary_files[0].get('build_command', '')
            if build_command:
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: {build_command}")
                    self._output(f"🧪 [ТЕСТ] В тестовом режиме сборка не выполняется")
                    # Симулируем успешную сборку
                    for binary in self.config.binary_files:
                        if binary.get('auto_rebuild', False):
                            self._output(f"🧪 [ТЕСТ] БЫЛ БЫ создан: {binary.get('name', '')}")
                else:
                    self._output(f"Запуск сборки: {build_command}")
                    exit_code, output = self._run_command(build_command.split(), capture_output=False)
                    
                    if exit_code != 0:
                        self._output(f"❌ ОШИБКА: Не удалось пересобрать бинарные файлы. Код выхода: {exit_code}")
                        return False
                    
                    # Проверяем наличие файлов
                    for binary in self.config.binary_files:
                        if not binary.get('auto_rebuild', False):
                            continue
                        binary_name = binary.get('name', '')
                        binary_path = os.path.join(self.project_dir, binary_name)
                        
                        if not os.path.exists(binary_path):
                            self._output(f"❌ ОШИБКА: Бинарный файл не был создан: {binary_name}")
                            return False
                        
                        if os.path.getsize(binary_path) == 0:
                            self._output(f"❌ ОШИБКА: Бинарный файл пуст: {binary_name}")
                            return False
                        
                        self._output(f"✓ Бинарный файл создан: {binary_name}")
                    
                    self._output("✓ Бинарные файлы успешно пересобраны")
                    return True
        
        return True
    
    def step_12_verify_versions(self) -> bool:
        """ШАГ 12: Проверка обновления версий"""
        self.current_step = 12
        self._output("=== ШАГ 12: Проверка обновления версий ===")
        
        errors = []
        
        for file in self.config.key_files:
            full_path = os.path.join(self.project_dir, file)
            if not os.path.isfile(full_path):
                continue
            
            ext = os.path.splitext(file)[1].lower()
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    if ext in ['.py', '.md']:
                        lines = f.readlines()[:20]
                        content = ''.join(lines)
                        
                        if self.new_version in content:
                            self._output(f"✓ Версия обновлена в {file}")
                        else:
                            # Проверяем наличие любой версии
                            match = re.search(r'V\d+\.\d+\.\d+', content)
                            if match:
                                old_ver = match.group(0)
                                errors.append(f"{file} (найдена: {old_ver}, ожидалось: {self.new_version})")
                            else:
                                self._output(f"ℹ Файл {file} не содержит версию в начале (пропускаем)")
                    
                    elif file == 'Version.txt' or file.endswith('Version.txt'):
                        content = f.read()
                        if f'APP_VERSION={self.new_version}' in content:
                            self._output(f"✓ Версия обновлена в {file} (APP_VERSION={self.new_version})")
                        else:
                            if 'APP_VERSION=' in content:
                                match = re.search(r'APP_VERSION=([^\n]+)', content)
                                old_ver = match.group(1) if match else "неизвестно"
                                errors.append(f"{file} (найдена: {old_ver}, ожидалось: {self.new_version})")
                            else:
                                errors.append(f"{file} (APP_VERSION не найден)")
            except Exception as e:
                errors.append(f"{file} (ошибка чтения: {e})")
        
        if errors:
            self._output(f"❌ ОШИБКА: Версия не обновлена в {len(errors)} файл(ах):")
            for error in errors:
                self._output(f"  - {error}")
            return False
        
        self._output("✓ Все версии успешно обновлены в ключевых файлах")
        return True
    
    def step_13_add_files_to_index(self) -> bool:
        """ШАГ 13: Добавление файлов в индекс"""
        self.current_step = 13
        self._output("=== ШАГ 13: Добавление файлов в индекс ===")
        
        # Добавляем измененные файлы
        for file in self.changed_files:
            if file:
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {file}")
                else:
                    exit_code, _ = self._run_command(['git', 'add', file])
                    if exit_code == 0:
                        self._output(f"✓ Добавлен: {file}")
        
        # Добавляем новые файлы
        for file in self.new_files:
            if file and os.path.isfile(os.path.join(self.project_dir, file)):
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {file}")
                else:
                    exit_code, _ = self._run_command(['git', 'add', file])
                    if exit_code == 0:
                        self._output(f"✓ Добавлен новый: {file}")
        
        # Добавляем новые директории
        for dir_path in self.new_dirs:
            if dir_path:
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {dir_path}")
                else:
                    exit_code, _ = self._run_command(['git', 'add', dir_path])
                    if exit_code == 0:
                        self._output(f"✓ Добавлена директория: {dir_path}")
        
        # Добавляем удаленные файлы
        for file in self.deleted_files:
            if file:
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {file}")
                else:
                    exit_code, _ = self._run_command(['git', 'add', file])
                    if exit_code == 0:
                        self._output(f"✓ Добавлен удаленный: {file}")
        
        # Добавляем файлы с версиями (отслеживаемые git)
        exit_code, output = self._run_command(['git', 'ls-files'])
        if exit_code == 0:
            tracked_files = output.strip().split('\n')
            for file in tracked_files:
                if not file:
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                if ext in self.config.file_extensions:
                    # Проверяем, был ли файл изменен
                    exit_code2, _ = self._run_command(['git', 'diff', '--quiet', 'HEAD', '--', file])
                    if exit_code2 != 0:  # Файл изменен
                        if self.test_mode:
                            self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {file}")
                        else:
                            exit_code3, _ = self._run_command(['git', 'add', file])
                            if exit_code3 == 0:
                                self._output(f"✓ Добавлен измененный: {file}")
        
        # Добавляем Version.txt явно
        version_file = self.config.version_file
        if os.path.exists(os.path.join(self.project_dir, version_file)):
            if self.test_mode:
                self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {version_file}")
            else:
                exit_code, _ = self._run_command(['git', 'add', version_file])
                if exit_code == 0:
                    self._output(f"✓ Добавлен: {version_file}")
        
        # Добавляем пересобранные бинарные файлы
        for binary in self.config.binary_files:
            # Поддерживаем и строки, и словари
            if isinstance(binary, str):
                binary_name = binary
            else:
                binary_name = binary.get('name', '') if isinstance(binary, dict) else str(binary)
            
            if binary_name and os.path.exists(os.path.join(self.project_dir, binary_name)):
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git add {binary_name}")
                else:
                    exit_code, _ = self._run_command(['git', 'add', binary_name])
                    if exit_code == 0:
                        self._output(f"✓ Добавлен пересобранный: {binary_name}")
        
        # Проверяем статус
        exit_code, output = self._run_command(['git', 'status', '--short'])
        if exit_code == 0:
            staged_files = [line for line in output.strip().split('\n') if line and line[0] in 'AMDR']
            if not staged_files:
                self._output("❌ ОШИБКА: Нет файлов в индексе для коммита")
                return False
            
            self._output(f"✓ Файлов в индексе: {len(staged_files)}")
        
        return True
    
    def step_13_5_pause_before_commit(self) -> bool:
        """ШАГ 13.5: ОБЯЗАТЕЛЬНАЯ ПАУЗА ПЕРЕД СОЗДАНИЕМ КОММИТА"""
        self.current_step = 13.5
        self._output("=== ШАГ 13.5: Ожидание подтверждения перед созданием коммита ===")
        self._output("")
        self._output("=== Файлы готовы к коммиту ===")
        self._output("")
        
        # Показываем список файлов
        exit_code, output = self._run_command(['git', 'diff', '--cached', '--name-only'])
        if exit_code == 0:
            self._output("Список файлов, которые будут включены в коммит:")
            self._output("----------------------------------------")
            self._output(output)
            self._output("----------------------------------------")
        
        self._output("")
        exit_code, output = self._run_command(['git', 'status', '--short'])
        if exit_code == 0:
            self._output("Полный статус индекса:")
            self._output("----------------------------------------")
            self._output(output)
            self._output("----------------------------------------")
        
        self._output("")
        self._output("🚨 КРИТИЧНО: ОБЯЗАТЕЛЬНАЯ ПАУЗА ДЛЯ АССИСТЕНТА 🚨")
        self._output("⏸ ПАУЗА: Ожидание подтверждения пользователя перед созданием коммита")
        
        self.is_paused = True
        return True
    
    def step_14_create_commit(self) -> bool:
        """ШАГ 14: Создание коммита"""
        self.current_step = 14
        self._output("=== ШАГ 14: Создание коммита ===")
        
        if not os.path.exists(self.commit_message_file):
            self._output("❌ ОШИБКА: Файл commit_message.txt не найден")
            return False
        
        if self.test_mode:
            self._output(f"🧪 [ТЕСТ] БЫЛО БЫ выполнено: git commit -F {self.commit_message_file}")
            self._output(f"🧪 [ТЕСТ] В тестовом режиме коммит НЕ создается")
            # Показываем что было бы в коммите
            if os.path.exists(self.commit_message_file):
                try:
                    with open(self.commit_message_file, 'r', encoding='utf-8') as f:
                        msg = f.read()
                        self._output(f"🧪 [ТЕСТ] Сообщение коммита:")
                        self._output(f"🧪 [ТЕСТ] {'-' * 50}")
                        for line in msg.split('\n'):
                            self._output(f"🧪 [ТЕСТ] {line}")
                        self._output(f"🧪 [ТЕСТ] {'-' * 50}")
                except Exception:
                    pass
            return True
        
        exit_code, output = self._run_command(['git', 'commit', '-F', self.commit_message_file])
        if exit_code != 0:
            self._output(f"❌ ОШИБКА: Не удалось создать коммит. Код выхода: {exit_code}")
            if output:
                self._output(output)
            return False
        
        self._output("✓ Коммит успешно создан")
        return True
    
    def step_15_verify_commit(self) -> bool:
        """ШАГ 15: Верификация коммита"""
        self.current_step = 15
        self._output("=== ШАГ 15: Верификация коммита ===")
        
        exit_code, output = self._run_command(['git', 'log', '-1', '--stat'])
        if exit_code != 0:
            self._output("❌ ОШИБКА: Не удалось получить информацию о последнем коммите")
            return False
        
        self._output(output)
        
        exit_code, commit_hash = self._run_command(['git', 'log', '-1', '--format=%H'])
        if exit_code == 0 and commit_hash.strip():
            self._output(f"✓ Коммит успешно создан: {commit_hash.strip()}")
            return True
        else:
            self._output("❌ ОШИБКА: Коммит не найден")
            return False
    
    def step_16_cleanup(self) -> bool:
        """ШАГ 16: Удаление временных файлов"""
        self.current_step = 16
        self._output("=== ШАГ 16: Удаление временных файлов ===")
        
        temp_files = [
            self.commit_message_file,
            self.vars_file,
            self.analysis_data_file
        ]
        
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                if self.test_mode:
                    self._output(f"🧪 [ТЕСТ] БЫЛО БЫ удалено: {os.path.basename(temp_file)}")
                else:
                    try:
                        os.remove(temp_file)
                        self._output(f"✓ Удален: {os.path.basename(temp_file)}")
                    except Exception as e:
                        self._output(f"⚠ Предупреждение: Не удалось удалить {temp_file}: {e}")
        
        return True
    
    def step_17_check_history_needed(self) -> bool:
        """ШАГ 17: Проверка необходимости истории"""
        self.current_step = 17
        self._output("=== ШАГ 17: Проверка необходимости истории ===")
        
        if not self.config.history_enabled:
            self._output("История отключена в настройках проекта")
            return True
        
        # Получаем список файлов из последнего коммита
        exit_code, output = self._run_command(['git', 'log', '-1', '--name-only', '--format='])
        if exit_code != 0:
            self._output("⚠ Предупреждение: Не удалось получить список файлов из коммита")
            return True
        
        committed_files = [f.strip() for f in output.strip().split('\n') if f.strip()]
        
        # Проверяем, есть ли среди них файлы для истории
        need_history = False
        for history_file in self.config.history_files:
            if history_file in committed_files:
                need_history = True
                break
        
        self.need_history = need_history
        self._output(f"NEED_HISTORY={'yes' if need_history else 'no'}")
        
        return True
    
    def step_18_create_history(self) -> bool:
        """ШАГ 18: Создание директории и копирование файлов (условно)"""
        self.current_step = 18
        
        if not getattr(self, 'need_history', False):
            self._output("История не требуется (ключевые файлы не изменялись)")
            return True
        
        self._output("=== ШАГ 18: Создание локальной истории ===")
        
        commit_date = datetime.now().strftime('%Y_%m_%d_%H_%M')
        history_dir = os.path.join(self.project_dir, self.config.history_directory, commit_date)
        
        if self.test_mode:
            self._output(f"🧪 [ТЕСТ] БЫЛО БЫ создано: {history_dir}")
            for history_file in self.config.history_files:
                source_path = os.path.join(self.project_dir, history_file)
                if os.path.exists(source_path):
                    self._output(f"🧪 [ТЕСТ] БЫЛ БЫ скопирован: {history_file} -> {history_dir}")
            copied_count = len([f for f in self.config.history_files if os.path.exists(os.path.join(self.project_dir, f))])
        else:
            try:
                os.makedirs(history_dir, exist_ok=True)
            except Exception as e:
                self._output(f"❌ ОШИБКА: Не удалось создать директорию истории: {e}")
                return False
            
            # Копируем файлы
            copied_count = 0
            for history_file in self.config.history_files:
                source_path = os.path.join(self.project_dir, history_file)
                if os.path.exists(source_path):
                    try:
                        import shutil
                        dest_path = os.path.join(history_dir, os.path.basename(history_file))
                        shutil.copy2(source_path, dest_path)
                        copied_count += 1
                    except Exception as e:
                        self._output(f"⚠ Предупреждение: Не удалось скопировать {history_file}: {e}")
        
        if copied_count > 0:
            self._output(f"✓ История создана: {history_dir} ({copied_count} файл(ов))")
            self.history_path = history_dir
        else:
            self._output("⚠ Предупреждение: Не удалось скопировать файлы в историю")
        
        return True
    
    def step_19_validate_history(self) -> bool:
        """ШАГ 19: Валидация истории (условно)"""
        self.current_step = 19
        
        if not getattr(self, 'need_history', False):
            return True
        
        self._output("=== ШАГ 19: Валидация истории ===")
        
        history_path = getattr(self, 'history_path', None)
        if not history_path or not os.path.isdir(history_path):
            self._output("❌ ОШИБКА: Директория истории не создана")
            return False
        
        files = os.listdir(history_path)
        if not files:
            self._output("❌ ОШИБКА: Файлы не скопированы в историю")
            return False
        
        self._output(f"✓ История валидирована: {len(files)} файл(ов)")
        return True
    
    def step_20_final_report(self) -> bool:
        """ШАГ 20: Подтверждение завершения и отчёт"""
        self.current_step = 20
        self._output("=== ШАГ 20: Подтверждение завершения и отчёт ===")
        self._output("=== Снимок (коммит) успешно создан! ===")
        self._output("")
        self._output("=== Отчёт о проделанной работе ===")
        self._output("")
        
        # Хеш коммита
        exit_code, commit_hash = self._run_command(['git', 'log', '-1', '--format=%H'])
        if exit_code == 0:
            self._output("Хеш коммита:")
            self._output(commit_hash.strip())
            self._output("")
        
        # Краткое сообщение
        exit_code, commit_msg = self._run_command(['git', 'log', '-1', '--format=%s'])
        if exit_code == 0:
            self._output("Краткое сообщение коммита:")
            self._output(commit_msg.strip())
            self._output("")
        
        # Изменённые файлы
        exit_code, files = self._run_command(['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'])
        if exit_code == 0:
            self._output("Изменённые файлы:")
            self._output(files.strip())
            self._output("")
        
        # Статистика
        exit_code, stats = self._run_command(['git', 'diff', '--stat', 'HEAD~1', 'HEAD'])
        if exit_code == 0:
            self._output("Статистика изменений:")
            self._output(stats.strip())
            self._output("")
        
        # История
        if getattr(self, 'need_history', False) and hasattr(self, 'history_path'):
            self._output("Локальная история создана:")
            self._output(self.history_path)
            self._output("")
        
        self._output("=== Процесс завершён успешно ===")
        return True
