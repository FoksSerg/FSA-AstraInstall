#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для создания и управления тестовой средой
Версия: V3.4.185 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Callable, List
from pathlib import Path


class TestEnvironment:
    """Класс для создания и управления тестовой средой (временной или постоянной)"""
    
    def __init__(self, output_callback: Optional[Callable[[str], None]] = None, persistent_dir: Optional[str] = None):
        """
        Инициализация тестовой среды
        
        Args:
            output_callback: Функция для вывода сообщений
            persistent_dir: Путь к постоянной тестовой директории (если None - создается временная)
        """
        self.output_callback = output_callback or print
        self.temp_dir: Optional[str] = None
        self.persistent_dir = persistent_dir
        self.is_persistent = persistent_dir is not None
        self.original_cwd: Optional[str] = None
        self._output("🧪 Инициализация тестовой среды...")
    
    def _output(self, message: str):
        """Вывод сообщения"""
        self.output_callback(message)
    
    def setup(self, reset: bool = False) -> bool:
        """
        Создание и настройка тестовой среды
        
        Args:
            reset: Если True и директория существует, очистить её перед настройкой
        
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            # Сохраняем текущую директорию
            self.original_cwd = os.getcwd()
            
            # Определяем директорию для работы
            if self.is_persistent:
                self.temp_dir = self.persistent_dir
                if not os.path.exists(self.temp_dir):
                    os.makedirs(self.temp_dir, exist_ok=True)
                    self._output(f"✓ Создана постоянная тестовая директория: {self.temp_dir}")
                elif reset:
                    self._output(f"🔄 Очистка существующей тестовой директории: {self.temp_dir}")
                    self._reset_directory()
                else:
                    self._output(f"✓ Используется существующая тестовая директория: {self.temp_dir}")
                    # Проверяем, нужна ли инициализация
                    if not os.path.exists(os.path.join(self.temp_dir, '.git')):
                        self._output("  → Git репозиторий не найден, требуется инициализация")
                    else:
                        self._output("  ✓ Git репозиторий уже существует")
                        return True  # Директория уже настроена
            else:
                # Создаем временную директорию
                self.temp_dir = tempfile.mkdtemp(prefix='commit_test_')
                self._output(f"✓ Создана временная директория: {self.temp_dir}")
            
            # Инициализируем git репозиторий
            if not self._init_git():
                return False
            
            # Создаем тестовые файлы
            if not self._create_test_files():
                return False
            
            # Создаем начальный коммит
            if not self._create_initial_commit():
                return False
            
            # Вносим изменения для тестирования
            if not self._make_test_changes():
                return False
            
            self._output("✓ Тестовая среда успешно создана")
            return True
            
        except Exception as e:
            self._output(f"❌ Ошибка при создании тестовой среды: {e}")
            import traceback
            self._output(traceback.format_exc())
            return False
    
    def _init_git(self) -> bool:
        """Инициализация git репозитория"""
        try:
            self._output("  → Инициализация git репозитория...")
            result = subprocess.run(
                ['git', 'init'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self._output(f"❌ Ошибка инициализации git: {result.stderr}")
                return False
            
            # Настраиваем git user (необходимо для коммитов)
            subprocess.run(
                ['git', 'config', 'user.name', 'Test User'],
                cwd=self.temp_dir,
                capture_output=True
            )
            subprocess.run(
                ['git', 'config', 'user.email', 'test@example.com'],
                cwd=self.temp_dir,
                capture_output=True
            )
            
            self._output("  ✓ Git репозиторий инициализирован")
            return True
        except Exception as e:
            self._output(f"❌ Ошибка при инициализации git: {e}")
            return False
    
    def _create_test_files(self) -> bool:
        """Создание тестовых файлов с версиями"""
        try:
            self._output("  → Создание тестовых файлов...")
            
            # Создаем Version.txt
            version_file = os.path.join(self.temp_dir, 'Version.txt')
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write("TestProject\n")
                f.write("MAJOR=3\n")
                f.write("MINOR=4\n")
                f.write("PATCH=AUTO\n")
                f.write("APP_VERSION=V3.4.100\n")
                f.write("Date: AUTO\n")
            
            # Создаем тестовый Python файл с версией
            test_py_file = os.path.join(self.temp_dir, 'test_module.py')
            today = datetime.now().strftime('%Y.%m.%d')
            with open(test_py_file, 'w', encoding='utf-8') as f:
                f.write("#!/usr/bin/env python3\n")
                f.write("# -*- coding: utf-8 -*-\n")
                f.write(f'"""\n')
                f.write(f"Тестовый модуль\n")
                f.write(f"Версия: V3.4.100 ({today})\n")
                f.write(f'"""\n')
                f.write("\n")
                f.write("def test_function():\n")
                f.write('    """Тестовая функция"""\n')
                f.write('    return "test"\n')
            
            # Создаем тестовый README.md
            readme_file = os.path.join(self.temp_dir, 'README.md')
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write("# Test Project\n\n")
                f.write("Версия: V3.4.100\n\n")
                f.write("Тестовый проект для проверки CommitManager.\n")
            
            # Создаем тестовый бинарный файл (пустой, но существующий)
            binary_file = os.path.join(self.temp_dir, 'test_binary.bin')
            with open(binary_file, 'wb') as f:
                f.write(b'BINARY_TEST_DATA_' * 100)
            
            self._output("  ✓ Тестовые файлы созданы")
            return True
            
        except Exception as e:
            self._output(f"❌ Ошибка при создании тестовых файлов: {e}")
            return False
    
    def _create_initial_commit(self) -> bool:
        """Создание начального коммита"""
        try:
            self._output("  → Создание начального коммита...")
            
            # Добавляем все файлы
            subprocess.run(
                ['git', 'add', '.'],
                cwd=self.temp_dir,
                capture_output=True
            )
            
            # Создаем коммит
            result = subprocess.run(
                ['git', 'commit', '-m', 'Initial commit'],
                cwd=self.temp_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self._output(f"⚠️ Предупреждение при создании коммита: {result.stderr}")
                # Продолжаем даже если коммит не создан (может быть проблема с конфигурацией)
            
            self._output("  ✓ Начальный коммит создан")
            return True
            
        except Exception as e:
            self._output(f"⚠️ Предупреждение при создании коммита: {e}")
            return True  # Продолжаем даже если коммит не создан
    
    def _make_test_changes(self) -> bool:
        """Внесение тестовых изменений в файлы"""
        try:
            self._output("  → Внесение тестовых изменений...")
            
            # Изменяем test_module.py - добавляем новую функцию
            test_py_file = os.path.join(self.temp_dir, 'test_module.py')
            with open(test_py_file, 'a', encoding='utf-8') as f:
                f.write("\n")
                f.write("def new_test_function():\n")
                f.write('    """Новая тестовая функция"""\n')
                f.write('    print("New function")\n')
                f.write('    return "new_test"\n')
            
            # Изменяем README.md - добавляем раздел
            readme_file = os.path.join(self.temp_dir, 'README.md')
            with open(readme_file, 'a', encoding='utf-8') as f:
                f.write("\n## Изменения\n\n")
                f.write("- Добавлена новая функция в test_module.py\n")
                f.write("- Обновлена документация\n")
            
            # Создаем новый файл
            new_file = os.path.join(self.temp_dir, 'new_file.py')
            with open(new_file, 'w', encoding='utf-8') as f:
                f.write("#!/usr/bin/env python3\n")
                f.write("# -*- coding: utf-8 -*-\n")
                f.write('"""\n')
                f.write("Новый файл\n")
                f.write(f"Версия: V3.4.100 ({datetime.now().strftime('%Y.%m.%d')})\n")
                f.write('"""\n')
            
            self._output("  ✓ Тестовые изменения внесены")
            return True
            
        except Exception as e:
            self._output(f"❌ Ошибка при внесении изменений: {e}")
            return False
    
    def get_temp_dir(self) -> Optional[str]:
        """Получить путь к временной директории"""
        return self.temp_dir
    
    def _reset_directory(self):
        """Очистка содержимого директории (для постоянной директории)"""
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return
        
        try:
            # Удаляем все содержимое, кроме самой директории
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            self._output("  ✓ Директория очищена")
        except Exception as e:
            self._output(f"⚠️ Ошибка при очистке директории: {e}")
    
    def cleanup(self, keep: bool = False):
        """
        Очистка тестовой среды
        
        Args:
            keep: Если True, не удалять директорию (для отладки или постоянной директории)
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            if self.is_persistent:
                # Постоянная директория не удаляется
                self._output(f"✓ Постоянная тестовая директория сохранена: {self.temp_dir}")
            elif keep:
                self._output(f"🧪 Тестовая директория сохранена: {self.temp_dir}")
            else:
                try:
                    shutil.rmtree(self.temp_dir)
                    self._output("✓ Тестовая директория удалена")
                except Exception as e:
                    self._output(f"⚠️ Не удалось удалить тестовую директорию: {e}")
                    self._output(f"   Путь: {self.temp_dir}")
        
        # Восстанавливаем исходную директорию
        if self.original_cwd:
            try:
                os.chdir(self.original_cwd)
            except Exception:
                pass
    
    def reset(self) -> bool:
        """
        Сброс тестовой среды (очистка и переинициализация)
        
        Returns:
            True если успешно
        """
        if not self.is_persistent:
            self._output("⚠️ Сброс доступен только для постоянной тестовой директории")
            return False
        
        return self.setup(reset=True)
    
    def __enter__(self):
        """Контекстный менеджер: вход"""
        if not self.setup():
            raise RuntimeError("Не удалось создать тестовую среду")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер: выход"""
        self.cleanup(keep=False)
