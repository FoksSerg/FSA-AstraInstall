#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт полного сканирования файловой системы Linux
Сканирует все файлы с правильной обработкой циклических симлинков
Результаты сохраняются в log файл для последующего анализа
"""

import os
import sys
import time
import datetime
from collections import defaultdict

# Настройки сканирования
ROOT_DIR = "/"  # Корневая директория (можно изменить)
# Директория для логов - по умолчанию рядом со скриптом
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = SCRIPT_DIR  # Директория для логов (по умолчанию - директория скрипта)

# Исключаемые пути (только виртуальные файловые системы и временные файлы)
# ВАЖНО: Для сравнения состояния системы до/после обновления сканируем ВСЕ реальные файлы
# Исключаем только:
# - Виртуальные файловые системы (proc, sys, dev) - не реальные файлы на диске
# - Временные файлы (tmp, run) - меняются между запусками и не отражают состояние системы
EXCLUDE_PATHS = [
    '/proc',      # Виртуальная файловая система процессов (не реальные файлы)
    '/sys',       # Виртуальная файловая система ядра (не реальные файлы)
    '/dev',       # Устройства (не реальные файлы на диске)
    '/tmp',       # Временные файлы (меняются между запусками)
    '/var/tmp',   # Временные файлы (меняются между запусками)
    '/run',       # Временные файлы рантайма (меняются между запусками)
    '/var/run',   # Временные файлы рантайма (меняются между запусками)
    '/lost+found', # Восстановленные файлы после fsck (не часть нормальной системы)
]

def should_exclude_path(path):
    """Проверка, нужно ли исключить путь"""
    for exclude_path in EXCLUDE_PATHS:
        if path.startswith(exclude_path):
            return True
    return False

def format_bytes(bytes_value):
    """Форматирование байтов в читаемый вид"""
    if bytes_value == 0:
        return "0 B"
    elif bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"

def format_time(seconds):
    """Форматирование времени"""
    if seconds < 60:
        return f"{seconds:.2f} сек"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} мин {secs:.2f} сек"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours} ч {minutes} мин {secs:.2f} сек"

class FullFilesystemScanner:
    """Сканер всей файловой системы"""
    
    def __init__(self, root_dir="/", log_file=None, log_dir=None):
        self.root_dir = root_dir
        self.files = {}  # {path: (size, mtime)}
        self.directories = set()
        self.files_scanned = 0
        self.directories_scanned = 0
        self.errors = []
        self.symlinks_skipped = 0
        self.cyclic_symlinks = []
        
        # Статистика по времени
        self.scan_start_time = None
        self.scan_end_time = None
        
        # Логирование
        if log_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Используем переданный log_dir или глобальный LOG_DIR (директория скрипта по умолчанию)
            if log_dir is None:
                log_dir = globals().get('LOG_DIR', SCRIPT_DIR)
            log_file = os.path.join(log_dir, f"full_scan_{timestamp}.log")
        
        self.log_file = log_file
        self.log_fd = None
        
    def log(self, message, print_to_console=True):
        """Логирование сообщения"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        if print_to_console:
            print(log_message)
        
        if self.log_fd:
            self.log_fd.write(log_message + "\n")
            self.log_fd.flush()
    
    def scan(self):
        """Основной метод сканирования"""
        # Открываем log файл
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            self.log_fd = open(self.log_file, 'w', encoding='utf-8')
        except Exception as e:
            print(f"⚠️  Не удалось открыть log файл {self.log_file}: {e}")
            self.log_fd = None
        
        self.log("=" * 80)
        self.log("🔍 НАЧАЛО ПОЛНОГО СКАНИРОВАНИЯ ФАЙЛОВОЙ СИСТЕМЫ")
        self.log("=" * 80)
        self.log(f"📁 Корневая директория: {self.root_dir}")
        self.log(f"📝 Log файл: {self.log_file}")
        self.log(f"🚫 Исключаемые пути: {len(EXCLUDE_PATHS)}")
        self.log("")
        
        if not os.path.exists(self.root_dir):
            self.log(f"❌ ОШИБКА: Директория {self.root_dir} не существует!")
            if self.log_fd:
                self.log_fd.close()
            return False
        
        self.scan_start_time = time.time()
        
        # Защита от циклических симлинков
        visited_paths = set()
        
        # Получаем реальный путь корневой директории
        try:
            root_real_path = os.path.realpath(self.root_dir)
        except (OSError, IOError):
            root_real_path = self.root_dir
        
        visited_paths.add(root_real_path)
        
        # Счетчик для неблокирующей работы
        files_processed = [0]
        chunk_size = 100  # Обрабатываем по 100 файлов, затем делаем паузу
        
        def scan_recursive(current_path, current_depth):
            """Рекурсивное сканирование директории"""
            nonlocal files_processed
            
            # Получаем реальный путь текущей директории
            try:
                real_path = os.path.realpath(current_path)
            except (OSError, IOError):
                real_path = current_path
            
            # Проверяем исключения
            if should_exclude_path(current_path):
                return
            
            # Проверяем циклические симлинки
            if real_path in visited_paths and current_depth > 0:
                if current_path not in [s[0] for s in self.cyclic_symlinks]:
                    self.cyclic_symlinks.append((current_path, real_path))
                return
            
            # Добавляем в посещенные
            if current_depth > 0:
                visited_paths.add(real_path)
            
            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        try:
                            # Проверяем тип файла (без следования симлинкам)
                            if entry.is_dir(follow_symlinks=False):
                                # Директория
                                rel_dir = os.path.relpath(entry.path, self.root_dir)
                                
                                # Проверяем исключения
                                if should_exclude_path(entry.path):
                                    continue
                                
                                if rel_dir != '.':
                                    self.directories.add(rel_dir)
                                    self.directories_scanned += 1
                                
                                # Проверяем циклический симлинк ПЕРЕД рекурсивным вызовом
                                try:
                                    entry_real_path = os.path.realpath(entry.path)
                                except (OSError, IOError):
                                    entry_real_path = entry.path
                                
                                # Если поддиректория указывает на корень - не рекурсируем (это цикл)
                                if entry_real_path == root_real_path:
                                    if entry.path not in [s[0] for s in self.cyclic_symlinks]:
                                        self.cyclic_symlinks.append((entry.path, entry_real_path))
                                    continue
                                
                                # Если уже посещена - не рекурсируем (это цикл)
                                if entry_real_path in visited_paths:
                                    if entry.path not in [s[0] for s in self.cyclic_symlinks]:
                                        self.cyclic_symlinks.append((entry.path, entry_real_path))
                                    continue
                                
                                # Рекурсивно сканируем поддиректорию
                                scan_recursive(entry.path, current_depth + 1)
                                
                            elif entry.is_file(follow_symlinks=False):
                                # Файл (реальный файл, не симлинк)
                                # ВАЖНО: entry.is_file(follow_symlinks=False) возвращает True только для реальных файлов,
                                # не для симлинков на файлы. Это гарантирует, что мы сканируем все реальные файлы.
                                if should_exclude_path(entry.path):
                                    continue
                                
                                try:
                                    stat = entry.stat()
                                    rel_path = os.path.relpath(entry.path, self.root_dir)
                                    
                                    # Сохраняем размер и время модификации
                                    # Используем rel_path как ключ - это гарантирует уникальность
                                    self.files[rel_path] = (stat.st_size, stat.st_mtime)
                                    self.files_scanned += 1
                                    files_processed[0] += 1
                                    
                                    # Делаем паузу каждые chunk_size файлов
                                    if files_processed[0] >= chunk_size:
                                        time.sleep(0.01)  # 10ms пауза
                                        files_processed[0] = 0
                                    
                                    # Периодически выводим прогресс
                                    if self.files_scanned % 10000 == 0:
                                        elapsed = time.time() - self.scan_start_time
                                        rate = self.files_scanned / elapsed if elapsed > 0 else 0
                                        self.log(f"📊 Прогресс: {self.files_scanned:,} файлов, {self.directories_scanned:,} директорий | "
                                                f"Скорость: {rate:.0f} файлов/сек | Время: {format_time(elapsed)}")
                                
                                except (OSError, IOError) as e:
                                    self.errors.append((entry.path, str(e)))
                                    continue
                            
                            else:
                                # Неизвестный тип записи (симлинк, сокет, FIFO и т.д.)
                                # ВАЖНО: entry.is_file(follow_symlinks=False) и entry.is_dir(follow_symlinks=False)
                                # возвращают False для симлинков, даже если они указывают на файлы/директории.
                                # Поэтому мы обрабатываем симлинки здесь.
                                try:
                                    # Проверяем циклический симлинк ПЕРЕД вызовом os.path.isdir()
                                    try:
                                        entry_real_path = os.path.realpath(entry.path)
                                    except (OSError, IOError):
                                        entry_real_path = entry.path
                                    
                                    # Если симлинк указывает на корень - пропускаем его (циклический)
                                    if entry_real_path == root_real_path:
                                        if entry.path not in [s[0] for s in self.cyclic_symlinks]:
                                            self.cyclic_symlinks.append((entry.path, entry_real_path))
                                        self.symlinks_skipped += 1
                                        continue
                                    
                                    # Если уже посещена - пропускаем (избегаем дубликатов)
                                    # ВАЖНО: Это означает, что если директория доступна по двум путям
                                    # (прямому и через симлинк), мы сканируем её только один раз.
                                    # Это правильно, так как файлы внутри уже были отсканированы.
                                    if entry_real_path in visited_paths:
                                        if entry.path not in [s[0] for s in self.cyclic_symlinks]:
                                            self.cyclic_symlinks.append((entry.path, entry_real_path))
                                        self.symlinks_skipped += 1
                                        continue
                                    
                                    # Проверяем, является ли это директорией через симлинк
                                    if os.path.isdir(entry.path):
                                        # Симлинк указывает на директорию
                                        rel_dir = os.path.relpath(entry.path, self.root_dir)
                                        
                                        if not should_exclude_path(entry.path):
                                            if rel_dir != '.':
                                                self.directories.add(rel_dir)
                                                self.directories_scanned += 1
                                            
                                            # Проверяем цикл еще раз перед рекурсией
                                            if entry_real_path == root_real_path:
                                                continue
                                            if entry_real_path in visited_paths:
                                                continue
                                            
                                            # Рекурсивно сканируем поддиректорию через симлинк
                                            # ВАЖНО: Файлы внутри этой директории будут отсканированы
                                            # через entry.is_file(follow_symlinks=False) в рекурсивном вызове
                                            scan_recursive(entry.path, current_depth + 1)
                                    elif os.path.isfile(entry.path):
                                        # Симлинк указывает на файл
                                        # ВАЖНО: Реальный файл уже был отсканирован через entry.is_file()
                                        # в директории, где он находится. Симлинк на файл - это просто
                                        # альтернативный путь к тому же файлу, поэтому мы его пропускаем.
                                        self.symlinks_skipped += 1
                                    else:
                                        # Это другой тип (сокет, FIFO, устройство и т.д.) - пропускаем
                                        self.symlinks_skipped += 1
                                
                                except (OSError, IOError) as e:
                                    self.errors.append((entry.path, str(e)))
                                    pass
                        
                        except (OSError, IOError) as e:
                            self.errors.append((entry.path if 'entry' in locals() else 'unknown', str(e)))
                            continue
            
            except (OSError, IOError) as e:
                self.errors.append((current_path, str(e)))
                pass
        
        try:
            self.log("🚀 Начало рекурсивного сканирования...")
            scan_recursive(self.root_dir, 0)
        except KeyboardInterrupt:
            self.log("⚠️  Сканирование прервано пользователем")
            if self.log_fd:
                self.log_fd.close()
            return False
        except Exception as e:
            self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            self.log(traceback.format_exc())
            if self.log_fd:
                self.log_fd.close()
            return False
        
        self.scan_end_time = time.time()
        self.scan_duration = self.scan_end_time - self.scan_start_time
        
        # Выводим результаты
        self.print_results()
        
        if self.log_fd:
            self.log_fd.close()
        
        return True
    
    def print_results(self):
        """Вывод результатов сканирования"""
        self.log("")
        self.log("=" * 80)
        self.log("📊 РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ")
        self.log("=" * 80)
        self.log("")
        
        # Основная статистика
        total_size = sum(size for size, _ in self.files.values())
        
        self.log(f"📁 Файлов: {self.files_scanned:,}")
        self.log(f"📂 Директорий: {self.directories_scanned:,}")
        self.log(f"💾 Общий размер: {format_bytes(total_size)}")
        self.log(f"⏱️  Время сканирования: {format_time(self.scan_duration)}")
        
        if self.scan_duration > 0:
            rate = self.files_scanned / self.scan_duration
            self.log(f"⚡ Скорость: {rate:.0f} файлов/сек")
        
        self.log("")
        
        # Статистика по ошибкам
        if self.errors:
            self.log(f"⚠️  Ошибок доступа: {len(self.errors)}")
            if len(self.errors) <= 10:
                for path, error in self.errors:
                    self.log(f"   • {path}: {error}")
            else:
                for path, error in self.errors[:10]:
                    self.log(f"   • {path}: {error}")
                self.log(f"   ... и еще {len(self.errors) - 10} ошибок")
        
        # Статистика по циклическим симлинкам
        if self.cyclic_symlinks:
            self.log(f"🔗 Циклических симлинков: {len(self.cyclic_symlinks)}")
            for symlink_path, real_path in self.cyclic_symlinks[:10]:
                self.log(f"   • {symlink_path} -> {real_path}")
            if len(self.cyclic_symlinks) > 10:
                self.log(f"   ... и еще {len(self.cyclic_symlinks) - 10} циклических симлинков")
        
        if self.symlinks_skipped > 0:
            self.log(f"🔗 Пропущено симлинков: {self.symlinks_skipped:,}")
        
        self.log("")
        
        # Статистика по размерам файлов
        if self.files:
            sizes = [size for size, _ in self.files.values()]
            total_size = sum(sizes)
            avg_size = total_size / len(sizes) if sizes else 0
            max_size = max(sizes) if sizes else 0
            
            # Находим самый большой файл
            largest_file = max(self.files.items(), key=lambda x: x[1][0]) if self.files else None
            
            self.log("📏 Статистика по размерам:")
            self.log(f"   • Средний размер: {format_bytes(avg_size)}")
            self.log(f"   • Максимальный размер: {format_bytes(max_size)}")
            if largest_file:
                self.log(f"   • Самый большой файл: {largest_file[0]} ({format_bytes(largest_file[1][0])})")
        
        self.log("")
        
        # Топ-10 директорий по количеству файлов
        dir_file_counts = defaultdict(int)
        for file_path in self.files.keys():
            dir_path = os.path.dirname(file_path)
            if dir_path:
                dir_file_counts[dir_path] += 1
        
        if dir_file_counts:
            top_dirs = sorted(dir_file_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            self.log("📂 Топ-10 директорий по количеству файлов:")
            for dir_path, count in top_dirs:
                self.log(f"   • {dir_path}: {count:,} файлов")
        
        self.log("")
        self.log("=" * 80)
        self.log("✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО")
        self.log("=" * 80)
        self.log("")
        self.log(f"📝 Полный отчет сохранен в: {self.log_file}")

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Полное сканирование файловой системы Linux')
    parser.add_argument('--root', '-r', default='/', help='Корневая директория для сканирования (по умолчанию: /)')
    parser.add_argument('--log-dir', '-l', default=LOG_DIR, help=f'Директория для log файлов (по умолчанию: {LOG_DIR})')
    parser.add_argument('--log-file', '-f', default=None, help='Имя log файла (по умолчанию: автоматически)')
    
    args = parser.parse_args()
    
    # Используем аргументы напрямую
    root_dir = args.root
    log_dir = args.log_dir
    
    print()
    print("=" * 80)
    print("🔍 ПОЛНОЕ СКАНИРОВАНИЕ ФАЙЛОВОЙ СИСТЕМЫ LINUX")
    print("=" * 80)
    print()
    print(f"📁 Корневая директория: {root_dir}")
    print(f"📝 Директория для логов: {log_dir}")
    print()
    print("⚠️  ВНИМАНИЕ: Сканирование может занять длительное время!")
    print("   Нажмите Ctrl+C для прерывания")
    print()
    
    scanner = FullFilesystemScanner(root_dir=root_dir, log_file=args.log_file, log_dir=log_dir)
    success = scanner.scan()
    
    if success:
        print()
        print("✅ Сканирование успешно завершено!")
        print(f"📝 Результаты сохранены в: {scanner.log_file}")
        return 0
    else:
        print()
        print("❌ Сканирование завершено с ошибками")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

