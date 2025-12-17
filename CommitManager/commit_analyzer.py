#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор изменений для CommitManager
Версия: V3.4.186 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import re
import fnmatch
import time
from datetime import datetime
from typing import Optional, Callable, List
from pathlib import Path
from .project_config import ProjectConfig
from .ai_agent_helper import create_ai_analysis_request, check_ai_analysis_complete


class CommitAnalyzer:
    """Класс для анализа изменений и формирования описания коммита"""
    
    def __init__(self, config: ProjectConfig, output_callback: Optional[Callable[[str], None]] = None):
        """
        Инициализация анализатора
        
        Args:
            config: Конфигурация проекта
            output_callback: Функция для вывода сообщений
        """
        self.config = config
        self.output_callback = output_callback or print
        self.project_dir = config.path
        self.analysis_data_file = os.path.join(self.project_dir, '.commit_analysis_data.txt')
        self.commit_message_file = os.path.join(self.project_dir, 'commit_message.txt')
        
        # Загружаем правила из .gitignore
        self.gitignore_patterns = self._load_gitignore_patterns()
    
    def _output(self, message: str):
        """Вывод сообщения через callback"""
        self.output_callback(message)
    
    def _load_gitignore_patterns(self) -> List[str]:
        """
        Загрузка паттернов из .gitignore файла
        
        Returns:
            Список паттернов для игнорирования
        """
        patterns = []
        gitignore_path = os.path.join(self.project_dir, '.gitignore')
        
        if not os.path.exists(gitignore_path):
            # Если .gitignore не найден, используем базовые паттерны
            return [
                '.commit_analysis_data.txt',
                '.commit_vars.sh',
                '.ai_commit_request.txt',
                'commit_message.txt',
                'Logs/',
                '*.log'
            ]
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Пропускаем пустые строки и комментарии
                    if not line or line.startswith('#'):
                        continue
                    # Убираем экранирование пробелов
                    line = line.replace('\\ ', ' ')
                    patterns.append(line)
        except Exception as e:
            self._output(f"⚠️ Предупреждение: Не удалось прочитать .gitignore: {e}")
            # Возвращаем базовые паттерны при ошибке
            return [
                '.commit_analysis_data.txt',
                '.commit_vars.sh',
                '.ai_commit_request.txt',
                'commit_message.txt',
                'Logs/',
                '*.log'
            ]
        
        return patterns
    
    def _should_ignore_file(self, file_path: str) -> bool:
        """
        Проверка, должен ли файл быть проигнорирован на основе .gitignore
        
        Args:
            file_path: Путь к файлу (относительно project_dir или абсолютный)
        
        Returns:
            True если файл должен быть проигнорирован
        """
        # Нормализуем путь
        if os.path.isabs(file_path):
            # Если абсолютный путь, делаем относительным к project_dir
            try:
                file_path = os.path.relpath(file_path, self.project_dir)
            except ValueError:
                # Если не в той же файловой системе, используем только имя файла
                file_path = os.path.basename(file_path)
        
        # Нормализуем разделители путей
        file_path = file_path.replace('\\', '/')
        
        # Проверяем каждый паттерн
        for pattern in self.gitignore_patterns:
            # Обрабатываем паттерны .gitignore
            # Убираем ведущий / для паттернов, начинающихся с /
            pattern_normalized = pattern.lstrip('/')
            
            # Проверяем точное совпадение имени файла
            file_name = os.path.basename(file_path)
            if fnmatch.fnmatch(file_name, pattern_normalized) or fnmatch.fnmatch(file_name, os.path.basename(pattern_normalized)):
                return True
            
            # Проверяем совпадение пути
            if fnmatch.fnmatch(file_path, pattern_normalized):
                return True
            
            # Проверяем совпадение с любым сегментом пути
            path_parts = file_path.split('/')
            for part in path_parts:
                if fnmatch.fnmatch(part, pattern_normalized):
                    return True
            
            # Проверяем паттерны с директориями (например, "Logs/" или "*/Logs/*")
            if '/' in pattern_normalized:
                if fnmatch.fnmatch(file_path, pattern_normalized):
                    return True
                # Проверяем, начинается ли путь с паттерна
                if file_path.startswith(pattern_normalized.rstrip('/')):
                    return True
        
        return False
    
    def analyze_changes(self, analysis_data_file: Optional[str] = None) -> bool:
        """
        Анализ изменений и формирование описания коммита
        
        Args:
            analysis_data_file: Путь к файлу с данными анализа. Если None, используется из конфига
        
        Returns:
            True если успешно, False в противном случае
        """
        if analysis_data_file is None:
            analysis_data_file = self.analysis_data_file
        
        if not os.path.exists(analysis_data_file):
            self._output(f"❌ ОШИБКА: Файл с данными анализа не найден: {analysis_data_file}")
            return False
        
        # Читаем данные анализа
        try:
            with open(analysis_data_file, 'r', encoding='utf-8') as f:
                analysis_data = f.read()
        except Exception as e:
            self._output(f"❌ ОШИБКА: Не удалось прочитать файл анализа: {e}")
            return False
        
        # Выбираем метод анализа
        if self.config.ai_method == 'api':
            return self._analyze_via_api(analysis_data)
        elif self.config.ai_method == 'hybrid':
            return self._analyze_hybrid(analysis_data)
        elif self.config.ai_method == 'local':
            return self._analyze_via_local_llm(analysis_data)
        else:  # manual
            return self._analyze_manual(analysis_data)
    
    def _analyze_via_api(self, analysis_data: str) -> bool:
        """Анализ через AI API (OpenAI/Anthropic)"""
        self._output("=== Анализ изменений через AI API ===")
        
        # Проверяем наличие API ключа
        if not self.config.ai_api_key:
            self._output("❌ ОШИБКА: API ключ не настроен. Используйте вкладку 'AI' для настройки.")
            return False
        
        # Формируем промпт
        prompt = self._build_prompt(analysis_data)
        
        # Вызываем API в зависимости от провайдера
        if self.config.ai_provider == 'openai':
            return self._call_openai_api(prompt)
        elif self.config.ai_provider == 'anthropic':
            return self._call_anthropic_api(prompt)
        else:
            self._output(f"❌ ОШИБКА: Неподдерживаемый провайдер: {self.config.ai_provider}")
            return False
    
    def _analyze_hybrid(self, analysis_data: str) -> bool:
        """
        Гибридный режим - автоматический анализ через AI-агента
        
        В этом режиме:
        1. Если есть API ключ - вызывается AI API для анализа
        2. Если нет API ключа:
           - Создается файл .ai_commit_request.txt для AI-агента (меня)
           - Ожидается создание commit_message.txt AI-агентом (до 45/30 секунд)
           - Если AI-агент не создал файл - процесс ОСТАНАВЛИВАЕТСЯ (fallback отключен)
        """
        self._output("=== Гибридный режим: Автоматический анализ изменений ===")
        
        # Если есть API ключ, используем API
        if self.config.ai_api_key:
            self._output("🤖 Использование AI API для анализа изменений...")
            return self._analyze_via_api(analysis_data)
        
        # Режим без API ключа - автоматическая работа с AI-агентом через файлы
        self._output("🤖 Режим автоматической работы с AI-агентом (без API ключа)")
        self._output("📝 Создаю запрос и автоматически открываю в Cursor...")
        
        try:
            # Создаем файл-запрос для AI-агента
            request_file = create_ai_analysis_request(
                self.project_dir,
                analysis_data,
                self.config.name
            )
            self._output(f"✓ Файл-запрос создан: {os.path.basename(request_file)}")
            
            # Создаем специальный файл-триггер для принудительного запуска AI-агента
            from .ai_agent_helper import create_ai_agent_trigger, send_to_ai_agent_automatically
            trigger_file = create_ai_agent_trigger(self.project_dir, request_file)
            self._output(f"✓ Файл-триггер создан: {os.path.basename(trigger_file)}")
            self._output("🚨 AI-агент должен автоматически обработать этот запрос!")
            
            # Автоматически отправляем запрос AI-агенту через создание нового чата
            # Используем только триггер-файл, который содержит всю необходимую информацию
            file_opened = send_to_ai_agent_automatically(trigger_file, self.project_dir)
            
            if file_opened:
                self._output("✓ Файл автоматически открыт в Cursor")
                self._output("💡 AI-агент автоматически прочитает файл через контекст Cursor")
                self._output("")
                self._output("⏳ Ожидание AI-агента (до 90 секунд)...")
                self._output("")
                
                # Даем время Cursor открыть файл (2 секунды)
                time.sleep(2)
                
                # Запоминаем время начала ожидания
                start_wait_time = time.time()
                
                # Удаляем старый commit_message.txt если он существует (от предыдущего запуска)
                commit_message_file = os.path.join(self.project_dir, 'commit_message.txt')
                if os.path.exists(commit_message_file):
                    try:
                        os.remove(commit_message_file)
                        self._output("🗑️ Удален старый commit_message.txt для проверки AI-агента")
                    except Exception:
                        pass
                
                # Ожидаем создания commit_message.txt AI-агентом (до 90 секунд = 1.5 минуты)
                max_wait_time = 90  # секунд
                check_interval = 1  # проверяем каждую секунду
                waited_time = 0
                
                while waited_time < max_wait_time:
                    if check_ai_analysis_complete(self.project_dir, start_wait_time):
                        # AI-агент создал файл
                        waited_time = int(time.time() - start_wait_time)
                        self._output(f"✓ AI-агент создал описание коммита (ожидание: {waited_time} сек)")
                        
                        # Закрываем файлы в Cursor после обработки
                        from .ai_agent_helper import close_files_in_cursor
                        files_to_close = [request_file, trigger_file]
                        if close_files_in_cursor(files_to_close):
                            self._output("✓ Временные файлы закрыты в Cursor")
                        else:
                            self._output("⚠️ Не удалось автоматически закрыть файлы в Cursor")
                        
                        return True
                    
                    time.sleep(check_interval)
                    waited_time = int(time.time() - start_wait_time)
                    
                    # Показываем прогресс каждые 5 секунд
                    if waited_time % 5 == 0:
                        self._output(f"⏳ Ожидание AI-агента... ({waited_time}/{max_wait_time} сек)")
                
                # AI-агент не создал файл - ОСТАНАВЛИВАЕМ ПРОЦЕСС
                self._output("")
                self._output("❌ КРИТИЧЕСКАЯ ОШИБКА: AI-агент не создал описание в течение 90 секунд")
                self._output("❌ Процесс остановлен - дальнейшие шаги невозможны без описания коммита")
                self._output("")
                self._output("💡 Действия:")
                self._output("   1. Проверьте, что файлы .ai_agent_trigger.txt и .ai_commit_request.txt открыты в Cursor")
                self._output("   2. Убедитесь, что AI-агент обработал запрос и создал commit_message.txt")
                self._output("   3. После создания файла запустите процесс заново")
                return False
            else:
                self._output("⚠️ Не удалось автоматически открыть файл в Cursor")
                self._output(f"💡 Файл создан: {request_file}")
                self._output("💡 Откройте файл вручную в Cursor для AI-анализа")
                self._output("")
                self._output("⏳ Ожидание AI-агента (до 90 секунд)...")
                self._output("")
                
                # Запоминаем время начала ожидания
                start_wait_time = time.time()
                
                # Удаляем старый commit_message.txt если он существует (от предыдущего запуска)
                commit_message_file = os.path.join(self.project_dir, 'commit_message.txt')
                if os.path.exists(commit_message_file):
                    try:
                        os.remove(commit_message_file)
                        self._output("🗑️ Удален старый commit_message.txt для проверки AI-агента")
                    except Exception:
                        pass
                
                # Ожидаем создания commit_message.txt AI-агентом (до 90 секунд = 1.5 минуты)
                max_wait_time = 90  # секунд
                check_interval = 1  # проверяем каждую секунду
                waited_time = 0
                
                while waited_time < max_wait_time:
                    if check_ai_analysis_complete(self.project_dir, start_wait_time):
                        # AI-агент создал файл
                        waited_time = int(time.time() - start_wait_time)
                        self._output(f"✓ AI-агент создал описание коммита (ожидание: {waited_time} сек)")
                        
                        # Закрываем файлы в Cursor после обработки
                        from .ai_agent_helper import close_files_in_cursor
                        files_to_close = [request_file]
                        if close_files_in_cursor(files_to_close):
                            self._output("✓ Временные файлы закрыты в Cursor")
                        else:
                            self._output("⚠️ Не удалось автоматически закрыть файлы в Cursor")
                        
                        return True
                    
                    time.sleep(check_interval)
                    waited_time = int(time.time() - start_wait_time)
                    
                    # Показываем прогресс каждые 5 секунд
                    if waited_time % 5 == 0:
                        self._output(f"⏳ Ожидание AI-агента... ({waited_time}/{max_wait_time} сек)")
                
                # AI-агент не создал файл - ОСТАНАВЛИВАЕМ ПРОЦЕСС
                self._output("")
                self._output("❌ КРИТИЧЕСКАЯ ОШИБКА: AI-агент не создал описание в течение 90 секунд")
                self._output("❌ Процесс остановлен - дальнейшие шаги невозможны без описания коммита")
                self._output("")
                self._output("💡 Действия:")
                self._output("   1. Проверьте, что файл .ai_commit_request.txt открыт в Cursor")
                self._output("   2. Убедитесь, что AI-агент обработал запрос и создал commit_message.txt")
                self._output("   3. После создания файла запустите процесс заново")
                return False
                
        except Exception as e:
            self._output(f"❌ ОШИБКА при автоматическом анализе: {e}")
            import traceback
            self._output(traceback.format_exc())
            self._output("❌ Процесс остановлен - дальнейшие шаги невозможны без описания коммита")
            return False
    
    def _parse_analysis_data_enhanced(self, analysis_data: str) -> str:
        """
        Улучшенный парсинг данных анализа с более интеллектуальным анализом изменений
        
        Args:
            analysis_data: Содержимое файла .commit_analysis_data.txt
        
        Returns:
            Строка с описанием коммита
        """
        # Используем .gitignore для определения игнорируемых файлов
        # Не нужно вручную прописывать список - все берется из .gitignore
        
        lines = analysis_data.split('\n')
        current_file = None
        changes_by_file = {}
        new_files = []
        deleted_files = []
        
        # Улучшенный парсинг данных
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if line_stripped.startswith('=== Файл:'):
                # Извлекаем имя файла
                file_match = re.search(r'=== Файл:\s*(.+?)(?:\s*\(новый\))?\s*===', line_stripped)
                if file_match:
                    current_file = file_match.group(1).strip()
                    
                    # Пропускаем файлы, которые игнорируются .gitignore
                    if self._should_ignore_file(current_file):
                        current_file = None
                        continue
                    
                    if '(новый)' in line_stripped:
                        new_files.append(current_file)
                    else:
                        if current_file not in changes_by_file:
                            changes_by_file[current_file] = []
            elif line_stripped.startswith('=== Директория:'):
                # Новая директория
                dir_match = re.search(r'=== Директория:\s*(.+?)(?:\s*\(новая\))?\s*===', line_stripped)
                if dir_match:
                    dir_name = dir_match.group(1).strip()
                    if '(новая)' in line_stripped:
                        new_files.append(f"{dir_name}/ (директория)")
            elif line_stripped.startswith('=== Удален:'):
                # Удаленный файл
                deleted_match = re.search(r'=== Удален:\s*(.+?)\s*===', line_stripped)
                if deleted_match:
                    deleted_files.append(deleted_match.group(1).strip())
            elif current_file and (line.startswith('+') or line.startswith('-')):
                # Изменения в файле (игнорируем изменения версий и дат)
                # Игнорируем технические строки
                if re.search(r'Версия|Version|дата|Date|V\d+\.\d+\.\d+|\d{4}\.\d{2}\.\d{2}|Статистика:|=== Файл:|=== Директория:', line, re.IGNORECASE):
                    continue
                
                # Игнорируем пустые строки и строки только с пробелами
                change_line = line[1:].strip()
                if not change_line or len(change_line) < 3:
                    continue
                
                # Игнорируем строки, которые выглядят как технические (содержат только символы, цифры, знаки)
                if re.match(r'^[+\-=\s\d]+$', change_line):
                    continue
                
                if current_file not in changes_by_file:
                    changes_by_file[current_file] = []
                
                if change_line:
                        # Улучшенная обработка изменений
                        if change_line.startswith('def ') or change_line.startswith('class '):
                            # Функция или класс
                            name = change_line.split('(')[0].split(':')[0].strip()
                            changes_by_file[current_file].append(f"Добавлена функция/класс: {name}")
                        elif change_line.startswith('import ') or change_line.startswith('from '):
                            # Импорт
                            if ' ' in change_line:
                                import_name = change_line.split(' ')[1].split('.')[0].split(' as ')[0]
                                changes_by_file[current_file].append(f"Добавлен импорт: {import_name}")
                        elif 'print(' in change_line or 'self._output(' in change_line or 'logger.' in change_line:
                            changes_by_file[current_file].append("Добавлен вывод/логирование")
                        elif change_line.startswith('#') and len(change_line) > 10:
                            # Комментарий
                            comment = change_line[1:].strip()[:80]
                            changes_by_file[current_file].append(f"Комментарий: {comment}")
                        elif len(change_line) > 20:
                            # Другое изменение - берем первые слова
                            words = change_line.split()[:8]
                            changes_by_file[current_file].append(' '.join(words) + '...')
        
        # Формируем улучшенное описание коммита
        today = datetime.now().strftime('%Y.%m.%d')
        message_parts = []
        
        # Фильтруем изменения - исключаем игнорируемые .gitignore файлы
        real_changes = {
            f: ch for f, ch in changes_by_file.items()
            if not self._should_ignore_file(f)
        }
        
        # Новые файлы (исключаем игнорируемые .gitignore)
        real_new_files = [
            f for f in new_files 
            if not self._should_ignore_file(f)
        ]
        
        # Улучшенный заголовок (только для реальных файлов)
        if real_changes:
            file_count = len(real_changes)
            if file_count == 1:
                first_file = list(real_changes.keys())[0]
                file_name = os.path.basename(first_file)
                message_parts.append(f"[Изменения в {file_name}]")
            else:
                message_parts.append(f"[Изменения в {file_count} файл(ах)]")
        elif real_new_files:
            message_parts.append(f"[Добавлены новые файлы: {len(real_new_files)}]")
        elif deleted_files:
            message_parts.append(f"[Удалены файлы: {len(deleted_files)}]")
        else:
            message_parts.append("[Изменения в проекте]")
        
        message_parts.append("")
        message_parts.append("Кратко, что изменили (списком):")
        message_parts.append("")
        
        # Группируем файлы по именам для устранения дубликатов
        files_by_name = {}
        for file, changes in real_changes.items():
            file_name = os.path.basename(file)
            if file_name not in files_by_name:
                files_by_name[file_name] = []
            files_by_name[file_name].append((file, changes))
        
        # Выводим файлы, группируя дубликаты
        for file_name, file_list in files_by_name.items():
            if len(file_list) == 1:
                # Один файл с таким именем - показываем полный путь если он не в корне
                file, changes = file_list[0]
                if '/' in file:
                    message_parts.append(f"{file}:")
                else:
                    message_parts.append(f"{file_name}:")
            else:
                # Несколько файлов с одинаковым именем - показываем все пути
                message_parts.append(f"{file_name} (в {len(file_list)} местах):")
                for file, changes in file_list:
                    message_parts.append(f"  - {file}")
            
            # Объединяем изменения из всех файлов с таким именем
            all_changes = []
            for _, changes in file_list:
                if changes:
                    all_changes.extend(changes)
            
            if all_changes:
                # Берем уникальные изменения (первые 3-5 наиболее значимых)
                unique_changes = []
                seen = set()
                for change in all_changes:
                    # Пропускаем слишком длинные или технические строки
                    if len(change) > 150:
                        continue
                    if change not in seen:
                        unique_changes.append(change)
                        seen.add(change)
                        if len(unique_changes) >= 5:
                            break
                
                if unique_changes:
                    for change in unique_changes:
                        # Ограничиваем длину описания
                        if len(change) > 100:
                            change = change[:97] + "..."
                        message_parts.append(f"- {change}")
                else:
                    message_parts.append("- Файл изменен")
            else:
                message_parts.append("- Файл изменен")
            message_parts.append("")
        
        if real_new_files:
            message_parts.append("Новые файлы:")
            for new_file in real_new_files[:10]:  # Ограничиваем количество
                file_name = os.path.basename(new_file) if '/' not in new_file else new_file
                message_parts.append(f"- {file_name}")
            message_parts.append("")
        
        # Удаленные файлы
        if deleted_files:
            message_parts.append("Описание удаленных классов/модулей:")
            for deleted_file in deleted_files[:10]:  # Ограничиваем количество
                file_name = os.path.basename(deleted_file)
                message_parts.append(f"- {file_name}")
            message_parts.append("")
        else:
            message_parts.append("Описание удаленных классов/модулей:")
            message_parts.append("- Нет удаленных компонентов")
            message_parts.append("")
        
        # Проект и дата
        message_parts.append(f"Проект: {self.config.name}")
        message_parts.append(f"Дата: {today}")
        
        return '\n'.join(message_parts)
    
    def _parse_analysis_data(self, analysis_data: str) -> str:
        """
        Парсинг данных анализа и формирование описания коммита
        
        Args:
            analysis_data: Содержимое файла .commit_analysis_data.txt
        
        Returns:
            Строка с описанием коммита
        """
        lines = analysis_data.split('\n')
        current_file = None
        changes_by_file = {}
        new_files = []
        
        # Парсим данные
        for line in lines:
            line = line.strip()
            if line.startswith('=== Файл:'):
                # Извлекаем имя файла
                file_match = re.search(r'=== Файл:\s*(.+?)(?:\s*\(новый\))?\s*===', line)
                if file_match:
                    current_file = file_match.group(1).strip()
                    if '(новый)' in line:
                        new_files.append(current_file)
                    else:
                        if current_file not in changes_by_file:
                            changes_by_file[current_file] = []
            elif line.startswith('=== Директория:'):
                # Новая директория
                dir_match = re.search(r'=== Директория:\s*(.+?)(?:\s*\(новая\))?\s*===', line)
                if dir_match:
                    dir_name = dir_match.group(1).strip()
                    if '(новая)' in line:
                        new_files.append(f"{dir_name}/ (директория)")
            elif current_file and (line.startswith('+') or line.startswith('-')):
                # Изменения в файле (игнорируем изменения версий и дат)
                if not re.search(r'Версия|Version|дата|Date|V\d+\.\d+\.\d+', line, re.IGNORECASE):
                    if current_file not in changes_by_file:
                        changes_by_file[current_file] = []
                    # Убираем префикс +/-
                    change_line = line[1:].strip()
                    if change_line and len(change_line) > 3:  # Минимальная длина для значимого изменения
                        changes_by_file[current_file].append(change_line[:100])  # Ограничиваем длину
        
        # Формируем описание коммита
        today = datetime.now().strftime('%Y.%m.%d')
        message_parts = []
        
        # Заголовок
        if changes_by_file:
            first_file = list(changes_by_file.keys())[0]
            if len(changes_by_file) == 1:
                message_parts.append(f"[Изменения в {first_file}]")
            else:
                message_parts.append(f"[Изменения в {len(changes_by_file)} файл(ах)]")
        elif new_files:
            message_parts.append(f"[Добавлены новые файлы]")
        else:
            message_parts.append("[Изменения в проекте]")
        
        message_parts.append("")
        message_parts.append("Кратко, что изменили (списком):")
        message_parts.append("")
        
        # Измененные файлы
        for file, changes in changes_by_file.items():
            message_parts.append(f"{file}:")
            if changes:
                # Берем первые 3-5 значимых изменений
                for change in changes[:5]:
                    # Упрощаем описание изменения
                    if change.startswith('def ') or change.startswith('class '):
                        message_parts.append(f"- Добавлена: {change.split('(')[0].split(':')[0].strip()}")
                    elif change.startswith('import ') or change.startswith('from '):
                        message_parts.append(f"- Добавлен импорт: {change.split(' ')[1].split('.')[0] if ' ' in change else change}")
                    elif 'print(' in change or 'self._output(' in change:
                        message_parts.append(f"- Добавлен вывод/логирование")
                    elif len(change) > 20:
                        # Берем первые слова как описание
                        words = change.split()[:5]
                        message_parts.append(f"- {(' '.join(words))}...")
                    else:
                        message_parts.append(f"- {change}")
            else:
                message_parts.append("- Файл изменен")
            message_parts.append("")
        
        # Новые файлы
        if new_files:
            message_parts.append("Новые файлы:")
            for new_file in new_files:
                message_parts.append(f"- {new_file}")
            message_parts.append("")
        
        # Удаленные компоненты
        message_parts.append("Описание удаленных классов/модулей:")
        message_parts.append("- Нет удаленных компонентов")
        message_parts.append("")
        
        # Проект и дата
        message_parts.append(f"Проект: {self.config.name}")
        message_parts.append(f"Дата: {today}")
        
        return '\n'.join(message_parts)
    
    def _analyze_via_local_llm(self, analysis_data: str) -> bool:
        """Анализ через локальную LLM модель"""
        self._output("=== Анализ через локальную LLM ===")
        self._output("⚠️ Функция пока не реализована")
        # TODO: Реализовать интеграцию с Ollama/LM Studio
        return False
    
    def _analyze_manual(self, analysis_data: str) -> bool:
        """Ручной анализ (без AI)"""
        self._output("=== Ручной режим: Требуется ручной ввод ===")
        self._output("⚠️ В ручном режиме описание коммита должно быть создано вручную")
        self._output(f"Сохраните описание в файл: {self.commit_message_file}")
        return True
    
    def _build_prompt(self, analysis_data: str) -> str:
        """Построить промпт для AI"""
        base_prompt = self.config.ai_prompt_template or """Проанализируй изменения в файлах проекта и создай краткое описание коммита на русском языке.

Формат описания:
[Заголовок коммита - опишите кратко основные изменения]

Кратко, что изменили (списком):

Имя_файла1:
- Краткое описание изменения 1
- Краткое описание изменения 2

Имя_файла2:
- Краткое описание изменения 1

Описание удаленных классов/модулей:
- Нет удаленных компонентов (или описание если есть)

Проект: {project}
Дата: {date}

ВАЖНО: НЕ комментировать изменения дат и версий в файлах проекта - эти изменения делаются автоматически.
В описании указывать ТОЛЬКО реальные изменения кода, логики, правил, структуры и т.д."""
        
        # Заменяем плейсхолдеры
        today = datetime.now().strftime('%Y.%m.%d')
        prompt = base_prompt.replace('{project}', self.config.name)
        prompt = base_prompt.replace('{date}', today)
        
        # Добавляем данные анализа
        prompt += f"\n\nДанные изменений:\n{analysis_data}"
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> bool:
        """Вызов OpenAI API"""
        try:
            # Проверяем наличие библиотеки requests
            try:
                import requests
            except ImportError:
                self._output("❌ ОШИБКА: Библиотека 'requests' не установлена")
                return False
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.ai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.config.ai_model,
                "messages": [
                    {"role": "system", "content": "Ты помощник для создания описаний коммитов на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config.ai_temperature,
                "max_tokens": self.config.ai_max_tokens
            }
            
            self._output("⏳ Отправка запроса к OpenAI API...")
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                message_content = result['choices'][0]['message']['content']
                
                # Сохраняем результат
                return self._save_commit_message(message_content)
            else:
                self._output(f"❌ ОШИБКА API: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self._output(f"❌ ОШИБКА при вызове OpenAI API: {e}")
            return False
    
    def _call_anthropic_api(self, prompt: str) -> bool:
        """Вызов Anthropic API"""
        self._output("⚠️ Интеграция с Anthropic API пока не реализована")
        # TODO: Реализовать вызов Anthropic API
        return False
    
    def _save_commit_message(self, message: str) -> bool:
        """Сохранить описание коммита в файл"""
        try:
            # Добавляем дату если её нет
            today = datetime.now().strftime('%Y.%m.%d')
            if 'Дата:' not in message:
                message += f"\n\nПроект: {self.config.name}\nДата: {today}"
            elif '{date}' in message:
                message = message.replace('{date}', today)
            
            # Заменяем плейсхолдер проекта
            message = message.replace('{project}', self.config.name)
            
            with open(self.commit_message_file, 'w', encoding='utf-8') as f:
                f.write(message)
            
            self._output(f"✓ Описание коммита сохранено в {self.commit_message_file}")
            return True
        except Exception as e:
            self._output(f"❌ ОШИБКА: Не удалось сохранить описание коммита: {e}")
            return False
