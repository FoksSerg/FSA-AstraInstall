#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль логирования для DockerManager
Версия: V3.1.158 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from io import StringIO

# ============================================================================
# ГЛОБАЛЬНЫЙ ЛОГ ФАЙЛ (один на сессию)
# ============================================================================

_global_log_file = None
_global_logger_initialized = False
_original_stdout = None
_original_stderr = None
_tee_handler = None

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================

def setup_logger(name="DockerManager", log_dir=None, force_new=False):
    """Настраивает логгер для DockerManager (один файл на сессию)"""
    global _global_log_file, _global_logger_initialized
    
    # Если уже инициализирован и не требуется новый файл - используем существующий
    if _global_logger_initialized and not force_new and _global_log_file:
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger, _global_log_file
    
    if log_dir is None:
        # Определяем папку для логов относительно DockerManager
        dockermanager_dir = Path(__file__).parent.absolute()
        log_dir = dockermanager_dir / "logs"
    
    # Создаем папку для логов
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Имя файла лога с timestamp (только если создаем новый)
    if force_new or _global_log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"dockermanager_{timestamp}.log"
        _global_log_file = log_file
    else:
        log_file = _global_log_file
    
    # Создаем корневой логгер DockerManager
    root_logger = logging.getLogger("DockerManager")
    root_logger.setLevel(logging.DEBUG)
    
    # Удаляем существующие обработчики только если создаем новый файл
    if force_new or not _global_logger_initialized:
        root_logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла (добавляем только если его еще нет)
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    if not has_file_handler:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Обработчик для консоли (только если его еще нет)
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                             for h in root_logger.handlers)
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(levelname)-8s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Получаем или создаем дочерний логгер
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Помечаем что инициализация выполнена
    if not _global_logger_initialized:
        root_logger.info(f"Логирование инициализировано: {log_file.name}")
        _global_logger_initialized = True
        
        # Настраиваем перехват stdout/stderr
        setup_stdout_stderr_capture()
    
    return logger, log_file

def get_logger(name="DockerManager"):
    """Получает существующий логгер (использует глобальный лог файл)"""
    global _global_log_file, _global_logger_initialized
    
    # Если логгер еще не инициализирован - инициализируем
    if not _global_logger_initialized:
        logger, log_file = setup_logger(name)
        return logger
    
    # Получаем существующий логгер
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Логгеры автоматически наследуют handlers от родителя "DockerManager"
    # если они являются дочерними (DockerManager.ServerConnection и т.д.)
    # Это работает автоматически через иерархию имен логгеров
    
    return logger

def get_log_file():
    """Возвращает путь к текущему лог файлу"""
    global _global_log_file
    return _global_log_file

# ============================================================================
# ПЕРЕХВАТ STDOUT/STDERR
# ============================================================================

class TeeOutput:
    """Класс для перехвата stdout/stderr и записи в лог"""
    def __init__(self, original_stream, logger, stream_name):
        self.original_stream = original_stream
        self.logger = logger
        self.stream_name = stream_name
        self.buffer = StringIO()
    
    def write(self, text):
        """Записывает в оригинальный поток и в лог"""
        if text.strip():  # Игнорируем пустые строки
            # Записываем в оригинальный поток
            self.original_stream.write(text)
            self.original_stream.flush()
            
            # Записываем в лог (убираем лишние переносы строк)
            lines = text.rstrip().split('\n')
            for line in lines:
                if line.strip():
                    self.logger.info(f"[{self.stream_name}] {line}")
        
        return len(text)
    
    def flush(self):
        """Сбрасывает буфер"""
        self.original_stream.flush()
    
    def __getattr__(self, name):
        """Проксирует все остальные атрибуты к оригинальному потоку"""
        return getattr(self.original_stream, name)

def setup_stdout_stderr_capture():
    """Настраивает перехват stdout/stderr для записи в лог"""
    global _original_stdout, _original_stderr, _tee_handler
    
    if _tee_handler is not None:
        return  # Уже настроено
    
    logger = logging.getLogger("DockerManager.Output")
    
    # Сохраняем оригинальные потоки
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    
    # Создаем Tee потоки
    sys.stdout = TeeOutput(_original_stdout, logger, "STDOUT")
    sys.stderr = TeeOutput(_original_stderr, logger, "STDERR")
    
    _tee_handler = True

def restore_stdout_stderr():
    """Восстанавливает оригинальные stdout/stderr"""
    global _original_stdout, _original_stderr, _tee_handler
    
    if _tee_handler is None:
        return
    
    if _original_stdout:
        sys.stdout = _original_stdout
    if _original_stderr:
        sys.stderr = _original_stderr
    
    _tee_handler = None

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def log_command(logger, command, description=""):
    """Логирует команду"""
    if description:
        logger.info(f"{description}: {command}")
    else:
        logger.info(f"Выполнение команды: {command}")

def log_result(logger, success, message="", error=None):
    """Логирует результат операции"""
    if success:
        logger.info(f"[OK] {message}")
    else:
        logger.error(f"[ERROR] {message}")
        if error:
            logger.error(f"Ошибка: {error}")

def log_step(logger, message):
    """Логирует шаг процесса"""
    logger.info(f"[#] {message}")

def log_success(logger, message):
    """Логирует успешную операцию"""
    logger.info(f"[OK] {message}")

def log_error(logger, message, exception=None):
    """Логирует ошибку"""
    logger.error(f"[ERROR] {message}")
    if exception:
        logger.exception(exception)

def log_info(logger, message):
    """Логирует информационное сообщение"""
    logger.info(f"[i] {message}")

def log_debug(logger, message):
    """Логирует отладочное сообщение"""
    logger.debug(f"[DEBUG] {message}")

