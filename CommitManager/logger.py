#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль логирования для CommitManager
Версия: V3.4.185 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
from datetime import datetime
from typing import Optional, Callable, TextIO


class CommitLogger:
    """Класс для логирования процесса создания коммита"""
    
    def __init__(self, project_dir: str, log_dir: Optional[str] = None):
        """
        Инициализация логгера
        
        Args:
            project_dir: Директория проекта
            log_dir: Директория для логов (если None, используется project_dir/Logs)
        """
        self.project_dir = project_dir
        
        # Определяем директорию для логов
        if log_dir:
            self.log_dir = log_dir
        else:
            self.log_dir = os.path.join(project_dir, 'Logs')
        
        # Создаем директорию для логов
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Создаем имя файла лога с датой и временем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(self.log_dir, f'commit_process_{timestamp}.log')
        
        # Открываем файл для записи
        self.log_handle: Optional[TextIO] = open(self.log_file, 'w', encoding='utf-8')
        
        # Записываем заголовок
        self._write_header()
    
    def _write_header(self):
        """Запись заголовка в лог"""
        if not self.log_handle:
            return
        
        header = f"""
{'=' * 80}
Лог процесса создания коммита
Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Директория проекта: {self.project_dir}
Файл лога: {self.log_file}
{'=' * 80}

"""
        self.log_handle.write(header)
        self.log_handle.flush()
    
    def log(self, message: str, level: str = 'INFO'):
        """
        Запись сообщения в лог
        
        Args:
            message: Текст сообщения
            level: Уровень логирования (INFO, ERROR, WARNING, DEBUG)
        """
        if not self.log_handle:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            self.log_handle.write(log_entry)
            self.log_handle.flush()  # Сбрасываем буфер для немедленной записи
        except Exception as e:
            # Если не удалось записать в лог, выводим в stderr
            print(f"Ошибка записи в лог: {e}", file=sys.stderr)
    
    def get_log_file_path(self) -> str:
        """Получить путь к файлу лога"""
        return self.log_file
    
    def close(self):
        """Закрыть файл лога"""
        if self.log_handle:
            footer = f"""
{'=' * 80}
Лог завершен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 80}
"""
            self.log_handle.write(footer)
            self.log_handle.close()
            self.log_handle = None
    
    def __enter__(self):
        """Контекстный менеджер: вход"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер: выход"""
        self.close()
    
    def __del__(self):
        """Деструктор: закрываем файл при удалении объекта"""
        if hasattr(self, 'log_handle') and self.log_handle:
            try:
                self.close()
            except Exception:
                pass


class LoggingOutputCallback:
    """Класс-обертка для одновременного вывода в GUI и в лог"""
    
    def __init__(self, gui_callback: Optional[Callable[[str], None]], logger: Optional[CommitLogger]):
        """
        Инициализация
        
        Args:
            gui_callback: Callback для вывода в GUI
            logger: Объект логгера
        """
        self.gui_callback = gui_callback
        self.logger = logger
    
    def __call__(self, message: str):
        """Вызов callback - вывод в GUI и в лог"""
        # Выводим в GUI
        if self.gui_callback:
            self.gui_callback(message)
        
        # Записываем в лог
        if self.logger:
            # Определяем уровень логирования по содержимому сообщения
            level = 'INFO'
            if '❌' in message or 'ОШИБКА' in message or 'ERROR' in message:
                level = 'ERROR'
            elif '⚠️' in message or 'Предупреждение' in message or 'WARNING' in message:
                level = 'WARNING'
            elif '🧪' in message or 'ТЕСТ' in message:
                level = 'DEBUG'
            
            self.logger.log(message, level)
