#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль самообновления FSA-AstraInstall

Проверяет наличие обновлений и заменяет текущий файл новым.
Работает как для бинарной версии, так и для Python версии.

Версия: V2.7.143 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import shutil
import tempfile
import subprocess
import re
from typing import Optional, Tuple
from datetime import datetime as dt

# ============================================================================
# КОНСТАНТЫ - ИСТОЧНИКИ ОБНОВЛЕНИЙ
# ============================================================================

# SMB сервер (приоритет - для разработки/тестирования)
SMB_SERVER = "10.10.55.77"
SMB_SHARE = "Install"
SMB_PATH = "ISO/Linux/Astra"

# Git репозиторий (fallback - для клиентов)
GIT_REPO = "https://github.com/ViRa-Realtime/FSA-AstraInstall"
GIT_BRANCH = "master"
GIT_RAW_URL = "https://raw.githubusercontent.com/ViRa-Realtime/FSA-AstraInstall"

# Имена файлов
BINARY_FILENAME = "FSA-AstraInstall"
PYTHON_FILENAME = "FSA-AstraInstall.py"
VERSION_SOURCE_FILE = "astra_automation.py"  # Файл для проверки версии

# Таймауты
TIMEOUT_CHECK = 10
TIMEOUT_DOWNLOAD = 300

# ============================================================================
# КЛАСС САМООБНОВЛЕНИЯ
# ============================================================================

class SelfUpdater:
    """Класс для самообновления файла."""
    
    def __init__(self, current_version: str):
        self.current_version = current_version
        self.is_frozen = getattr(sys, 'frozen', False)
        
        # Определяем какой файл обновляем
        if self.is_frozen:
            self.update_filename = BINARY_FILENAME
            self.current_path = sys.executable
        else:
            self.update_filename = PYTHON_FILENAME
            self.current_path = os.path.abspath(sys.argv[0])
        
        self.available_version: Optional[str] = None
        self.selected_source: Optional[str] = None  # 'smb' или 'git'
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = dt.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    # ========================================================================
    # ПАРСИНГ ВЕРСИЙ
    # ========================================================================
    
    def parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Парсит версию в кортеж (major, minor, patch)."""
        clean = version_str.strip().upper()
        if clean.startswith('V'):
            clean = clean[1:]
        if '(' in clean:
            clean = clean.split('(')[0].strip()
        parts = clean.split('.')
        try:
            return (
                int(parts[0]) if len(parts) > 0 else 0,
                int(parts[1]) if len(parts) > 1 else 0,
                int(parts[2]) if len(parts) > 2 else 0
            )
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Сравнивает версии: -1 если v1<v2, 0 если равны, 1 если v1>v2."""
        p1, p2 = self.parse_version(v1), self.parse_version(v2)
        return -1 if p1 < p2 else (1 if p1 > p2 else 0)
    
    def extract_version_from_content(self, content: str) -> Optional[str]:
        """Извлекает версию из содержимого файла."""
        # APP_VERSION = "V2.6.141 (2025.12.02)"
        match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        # Версия: V2.6.141
        match = re.search(r'Версия:\s*(V[\d.]+)', content)
        if match:
            return match.group(1)
        return None
    
    # ========================================================================
    # ПРОВЕРКА SMB
    # ========================================================================
    
    def check_smb_available(self) -> bool:
        """Проверяет доступность SMB сервера."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', SMB_SERVER],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_version_from_smb(self) -> Optional[str]:
        """Получает версию с SMB."""
        try:
            remote_file = f"{SMB_PATH}/{VERSION_SOURCE_FILE}"
            
            # Читаем первые 5KB файла
            cmd = ['smbclient', f'//{SMB_SERVER}/{SMB_SHARE}', '-N',
                   '-c', f'get {remote_file} -']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_CHECK)
            
            if result.returncode == 0:
                return self.extract_version_from_content(result.stdout[:5000])
            return None
        except Exception:
            return None
    
    def download_from_smb(self, dest_path: str) -> bool:
        """Скачивает файл с SMB."""
        try:
            remote_file = f"{SMB_PATH}/{self.update_filename}"
            self.log(f"Скачивание с SMB: //{SMB_SERVER}/{SMB_SHARE}/{remote_file}")
            
            cmd = ['smbclient', f'//{SMB_SERVER}/{SMB_SHARE}', '-N',
                   '-c', f'get {remote_file} {dest_path}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_DOWNLOAD)
            
            if result.returncode == 0 and os.path.exists(dest_path):
                size = os.path.getsize(dest_path) / 1024 / 1024
                self.log(f"Скачано: {size:.2f} MB")
                return True
            return False
        except Exception as e:
            self.log(f"Ошибка SMB: {e}", "ERROR")
            return False
    
    # ========================================================================
    # ПРОВЕРКА GIT
    # ========================================================================
    
    def check_git_available(self) -> bool:
        """Проверяет доступность Git репозитория."""
        try:
            url = f"{GIT_RAW_URL}/{GIT_BRANCH}/README.md"
            result = subprocess.run(
                ['curl', '-s', '-f', '--max-time', '5', '-I', url],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_version_from_git(self) -> Optional[str]:
        """Получает версию с Git."""
        try:
            url = f"{GIT_RAW_URL}/{GIT_BRANCH}/{VERSION_SOURCE_FILE}"
            result = subprocess.run(
                ['curl', '-s', '-f', '--max-time', str(TIMEOUT_CHECK), url],
                capture_output=True, text=True, timeout=TIMEOUT_CHECK + 5
            )
            
            if result.returncode == 0:
                return self.extract_version_from_content(result.stdout[:5000])
            return None
        except Exception:
            return None
    
    def download_from_git(self, dest_path: str) -> bool:
        """Скачивает файл с Git."""
        try:
            url = f"{GIT_RAW_URL}/{GIT_BRANCH}/{self.update_filename}"
            self.log(f"Скачивание с Git: {url}")
            
            result = subprocess.run(
                ['curl', '-L', '-f', '-o', dest_path, '--max-time', str(TIMEOUT_DOWNLOAD), url],
                capture_output=True, text=True, timeout=TIMEOUT_DOWNLOAD + 30
            )
            
            if result.returncode == 0 and os.path.exists(dest_path):
                size = os.path.getsize(dest_path) / 1024 / 1024
                self.log(f"Скачано: {size:.2f} MB")
                return True
            return False
        except Exception as e:
            self.log(f"Ошибка Git: {e}", "ERROR")
            return False
    
    # ========================================================================
    # ПРОВЕРКА ОБНОВЛЕНИЙ
    # ========================================================================
    
    def check_for_updates(self) -> Optional[str]:
        """
        Проверяет наличие обновлений.
        Возвращает новую версию или None.
        """
        self.log(f"Проверка обновлений (текущая: {self.current_version})")
        
        # 1. Пробуем SMB (приоритет)
        self.log(f"Источник: SMB {SMB_SERVER}...")
        if self.check_smb_available():
            version = self.get_version_from_smb()
            if version:
                self.log(f"SMB версия: {version}")
                if self.compare_versions(version, self.current_version) > 0:
                    self.available_version = version
                    self.selected_source = 'smb'
                    return version
                else:
                    self.log("✓ Установлена актуальная версия")
                    return None
        else:
            self.log("SMB недоступен", "WARNING")
        
        # 2. Пробуем Git (fallback)
        self.log(f"Источник: Git...")
        if self.check_git_available():
            version = self.get_version_from_git()
            if version:
                self.log(f"Git версия: {version}")
                if self.compare_versions(version, self.current_version) > 0:
                    self.available_version = version
                    self.selected_source = 'git'
                    return version
                else:
                    self.log("✓ Установлена актуальная версия")
                    return None
        else:
            self.log("Git недоступен", "WARNING")
        
        self.log("Не удалось проверить обновления", "WARNING")
        return None
    
    # ========================================================================
    # ПРИМЕНЕНИЕ ОБНОВЛЕНИЯ
    # ========================================================================
    
    def verify_file(self, file_path: str) -> bool:
        """Проверяет скачанный файл."""
        if not os.path.exists(file_path):
            return False
        
        size = os.path.getsize(file_path)
        if size < 1000:
            self.log(f"Файл слишком маленький: {size} байт", "ERROR")
            return False
        
        # Для бинарника проверяем ELF
        if self.is_frozen:
            with open(file_path, 'rb') as f:
                if f.read(4) != b'\x7fELF':
                    self.log("Файл не является ELF", "ERROR")
                    return False
        else:
            # Для Python проверяем shebang
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                if not ('python' in first_line.lower() or first_line.startswith('#!')):
                    self.log("Файл не является Python скриптом", "ERROR")
                    return False
        
        return True
    
    def apply_update(self, new_file_path: str) -> bool:
        """Заменяет текущий файл новым."""
        backup_path = self.current_path + ".backup"
        
        self.log(f"Применение обновления...")
        
        try:
            # Резервная копия
            shutil.copy2(self.current_path, backup_path)
            
            # Замена
            shutil.move(new_file_path, self.current_path)
            os.chmod(self.current_path, 0o755)
            
            # Удаляем backup
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            self.log("✓ Обновление применено!")
            return True
            
        except Exception as e:
            self.log(f"Ошибка: {e}", "ERROR")
            if os.path.exists(backup_path):
                shutil.move(backup_path, self.current_path)
            return False
    
    def restart(self):
        """Перезапускает приложение."""
        if self.is_frozen:
            args = [self.current_path, '--skip-update']
        else:
            args = [sys.executable, self.current_path, '--skip-update']
        
        # Добавляем оригинальные аргументы
        for arg in sys.argv[1:]:
            if arg not in ('--force-update', '--skip-update'):
                args.append(arg)
        
        self.log(f"Перезапуск: {' '.join(args)}")
        os.execv(args[0], args)
    
    # ========================================================================
    # ГЛАВНЫЕ МЕТОДЫ
    # ========================================================================
    
    def download_and_apply(self) -> bool:
        """Скачивает и применяет обновление."""
        # Если источник не выбран — сначала проверяем
        if not self.selected_source:
            if not self.check_for_updates():
                self.log("Нет доступных обновлений")
                return False
        
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='_update') as tmp:
            tmp_path = tmp.name
        
        try:
            # Скачиваем
            if self.selected_source == 'smb':
                success = self.download_from_smb(tmp_path)
            else:
                success = self.download_from_git(tmp_path)
            
            if not success:
                return False
            
            # Проверяем
            if not self.verify_file(tmp_path):
                os.remove(tmp_path)
                return False
            
            # Применяем
            return self.apply_update(tmp_path)
            
        except Exception as e:
            self.log(f"Ошибка: {e}", "ERROR")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False
    
    def update_and_restart(self) -> bool:
        """Полный цикл: скачать, применить, перезапустить."""
        if self.download_and_apply():
            self.log(f"Обновление до {self.available_version} завершено!")
            self.restart()
            return True
        return False


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

if __name__ == '__main__':
    print("=" * 50)
    print("=== Тест SelfUpdater ===")
    print("=" * 50)
    
    updater = SelfUpdater("V2.6.141")
    print(f"Тип: {'бинарник' if updater.is_frozen else 'Python'}")
    print(f"Файл: {updater.update_filename}")
    print(f"Путь: {updater.current_path}")
    
    print("\n--- Проверка источников ---")
    print(f"SMB ({SMB_SERVER}): {'✓' if updater.check_smb_available() else '✗'}")
    print(f"Git: {'✓' if updater.check_git_available() else '✗'}")
    
    print("\n--- Проверка обновлений ---")
    new_ver = updater.check_for_updates()
    if new_ver:
        print(f"Доступно: {new_ver} (источник: {updater.selected_source})")
    else:
        print("Обновлений нет")
    
    print("=" * 50)
