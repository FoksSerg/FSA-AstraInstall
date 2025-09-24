#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль перехвата интерактивных запросов для автоматизации установки
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import threading
import time
import re

class InteractiveHandler(object):
    """Класс для перехвата и автоматических ответов на интерактивные запросы"""
    
    def __init__(self):
        self.patterns = {
            'dpkg_config': r'\*\*\* .* \(Y/I/N/O/D/Z\) \[.*\] \?',
            'apt_config': r'Настройка пакета',
            'keyboard_config': r'Выберите подходящую раскладку клавиатуры',
            'keyboard_switch': r'способ переключения клавиатуры между национальной раскладкой',
            'language_config': r'Выберите язык системы'
        }
        
        self.responses = {
            'dpkg_config': 'Y',      # Всегда соглашаемся с новыми версиями
            'apt_config': '',        # Принимаем настройки по умолчанию (Enter)
            'keyboard_config': '',   # Принимаем предложенную раскладку (Enter)
            'keyboard_switch': '',   # Принимаем способ переключения (Enter)
            'language_config': ''    # Принимаем язык системы (Enter)
        }
    
    def detect_interactive_prompt(self, output):
        """Обнаружение интерактивного запроса в выводе"""
        for prompt_type, pattern in self.patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                return prompt_type
        return None
    
    def get_auto_response(self, prompt_type):
        """Получение автоматического ответа для типа запроса"""
        return self.responses.get(prompt_type, 'Y')  # По умолчанию всегда "Y"
    
    def run_command_with_interactive_handling(self, cmd, dry_run=False):
        """Запуск команды с перехватом интерактивных запросов"""
        if dry_run:
            print("⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: команда НЕ выполняется (только симуляция)")
            print("   Команда: %s" % ' '.join(cmd))
            return 0
        
        print("🚀 Выполнение команды с автоматическими ответами...")
        print("   Команда: %s" % ' '.join(cmd))
        
        try:
            # Запускаем процесс
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Читаем вывод построчно
            output_buffer = ""
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку
                print("   %s" % line.rstrip())
                
                # Добавляем в буфер для анализа
                output_buffer += line
                
                # Проверяем на интерактивные запросы
                prompt_type = self.detect_interactive_prompt(output_buffer)
                if prompt_type:
                    response = self.get_auto_response(prompt_type)
                    print("   🤖 Автоматический ответ: %s (для %s)" % (response, prompt_type))
                    
                    # Отправляем ответ
                    process.stdin.write(response + '\n')
                    process.stdin.flush()
                    
                    # Очищаем буфер
                    output_buffer = ""
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            if return_code == 0:
                print("   ✅ Команда выполнена успешно")
            else:
                print("   ❌ Команда завершилась с ошибкой (код: %d)" % return_code)
            
            return return_code
            
        except Exception as e:
            print("   ❌ Ошибка выполнения команды: %s" % str(e))
            return 1
    
    def simulate_interactive_scenarios(self):
        """Симуляция различных интерактивных сценариев для тестирования"""
        print("🧪 Симуляция интерактивных сценариев...")
        
        # Тест 1: dpkg конфигурационный файл
        print("\n📋 Тест 1: dpkg конфигурационный файл")
        test_output = """Файл настройки «/etc/ssl/openssl.cnf»
==> Изменён с момента установки (вами или сценарием).
==> Автор пакета предоставил обновлённую версию.
*** openssl.cnf (Y/I/N/O/D/Z) [по умолчанию N] ?"""
        
        prompt_type = self.detect_interactive_prompt(test_output)
        if prompt_type:
            response = self.get_auto_response(prompt_type)
            print("   ✅ Обнаружен запрос: %s" % prompt_type)
            if response == '':
                print("   ✅ Автоматический ответ: Enter (пустой ответ)")
            else:
                print("   ✅ Автоматический ответ: %s" % response)
        else:
            print("   ❌ Запрос не обнаружен")
        
        # Тест 2: настройка клавиатуры
        print("\n⌨️ Тест 2: настройка клавиатуры")
        test_output = """Настройка пакета
Настраивается keyboard-configuration
Выберите подходящую раскладку клавиатуры."""
        
        prompt_type = self.detect_interactive_prompt(test_output)
        if prompt_type:
            response = self.get_auto_response(prompt_type)
            print("   ✅ Обнаружен запрос: %s" % prompt_type)
            if response == '':
                print("   ✅ Автоматический ответ: Enter (пустой ответ)")
            else:
                print("   ✅ Автоматический ответ: %s" % response)
        else:
            print("   ❌ Запрос не обнаружен")
        
        # Тест 3: способ переключения клавиатуры
        print("\n🔄 Тест 3: способ переключения клавиатуры")
        test_output = """Вам нужно указать способ переключения клавиатуры между национальной раскладкой и стандартной латинской раскладкой."""
        
        prompt_type = self.detect_interactive_prompt(test_output)
        if prompt_type:
            response = self.get_auto_response(prompt_type)
            print("   ✅ Обнаружен запрос: %s" % prompt_type)
            if response == '':
                print("   ✅ Автоматический ответ: Enter (пустой ответ)")
            else:
                print("   ✅ Автоматический ответ: %s" % response)
        else:
            print("   ❌ Запрос не обнаружен")
        
        print("\n✅ Симуляция завершена")

def main(dry_run=False):
    """Основная функция для тестирования"""
    handler = InteractiveHandler()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с системными командами")
        print("Запустите: sudo python interactive_handler.py")
        return False
    
    # Симулируем интерактивные сценарии
    handler.simulate_interactive_scenarios()
    
    # Тестируем реальную команду (если не dry-run)
    if not dry_run:
        print("\n🔧 Тест реальной команды...")
        # Пример команды, которая может вызвать интерактивные запросы
        test_cmd = ['apt-get', 'install', '--simulate', 'openssl']
        result = handler.run_command_with_interactive_handling(test_cmd, dry_run)
        
        if result == 0:
            print("✅ Тест реальной команды завершен успешно")
        else:
            print("❌ Тест реальной команды завершен с ошибкой")
    else:
        print("\n⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: реальные команды не выполняются")
    
    return True

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("=" * 60)
    if dry_run:
        print("Тест модуля перехвата интерактивных запросов (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля перехвата интерактивных запросов")
    print("=" * 60)
    
    success = main(dry_run)
    
    if success:
        if dry_run:
            print("\n✅ Тест модуля завершен! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("\n✅ Тест модуля завершен!")
    else:
        print("\n❌ Ошибка теста модуля")
        sys.exit(1)
