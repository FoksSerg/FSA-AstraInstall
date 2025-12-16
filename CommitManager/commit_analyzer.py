#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор изменений для CommitManager
Версия: V3.4.184 (2025.12.16)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import re
from datetime import datetime
from typing import Optional, Callable
from .project_config import ProjectConfig


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
    
    def _output(self, message: str):
        """Вывод сообщения через callback"""
        self.output_callback(message)
    
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
        """Гибридный режим - ожидание ассистента в Cursor IDE"""
        self._output("=== Гибридный режим: Ожидание анализа ассистентом ===")
        self._output("⏸ ПАУЗА: Ожидание анализа ассистентом в Cursor IDE")
        self._output("")
        self._output("Инструкция для ассистента:")
        self._output("1. Прочитайте данные из файла: .commit_analysis_data.txt")
        self._output("2. Проанализируйте все изменения в файлах")
        self._output("3. Сформируйте описание коммита в формате:")
        self._output("   [Заголовок коммита]")
        self._output("   ")
        self._output("   Имя_файла:")
        self._output("   - Описание изменения")
        self._output("   ")
        self._output("   Проект: {project}")
        self._output("   Дата: {date}")
        self._output("4. Сохраните описание в файл: commit_message.txt")
        self._output("")
        self._output("⚠️ ВАЖНО: НЕ комментировать изменения дат и версий!")
        self._output("")
        
        # Создаем маркерный файл для ожидания
        marker_file = os.path.join(self.project_dir, '.wait_for_assistant.txt')
        try:
            with open(marker_file, 'w', encoding='utf-8') as f:
                f.write(f"Ожидание анализа ассистентом\n")
                f.write(f"Время создания: {datetime.now().isoformat()}\n")
                f.write(f"Файл данных: {self.analysis_data_file}\n")
                f.write(f"Файл результата: {self.commit_message_file}\n")
        except Exception as e:
            self._output(f"⚠️ Предупреждение: Не удалось создать маркерный файл: {e}")
        
        # В гибридном режиме мы просто ждем, пока файл commit_message.txt не появится
        # Это будет обрабатываться в GUI
        return True
    
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
