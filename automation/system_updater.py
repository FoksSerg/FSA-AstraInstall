#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль обновления системы с автоматическими ответами
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import re

class SystemUpdater(object):
    """Класс для обновления системы с автоматическими ответами"""
    
    def __init__(self):
        self.patterns = {
            'dpkg_config': r'\*\*\* .* \(Y/I/N/O/D/Z\) \[.*\] \?',
            'apt_config': r'Настройка пакета',
            'keyboard_config': r'Выберите подходящую раскладку клавиатуры',
            'keyboard_switch': r'способ переключения клавиатуры между национальной раскладкой',
            'language_config': r'Выберите язык системы',
            'restart_services': r'Перезапустить службы во время пакетных операций'
        }
        
        self.responses = {
            'dpkg_config': 'Y',      # Соглашаемся с новыми версиями
            'apt_config': '',        # Принимаем настройки по умолчанию (Enter)
            'keyboard_config': '',   # Принимаем предложенную раскладку (Enter)
            'keyboard_switch': '',   # Принимаем способ переключения (Enter)
            'language_config': '',   # Принимаем язык системы (Enter)
            'restart_services': 'Y'  # Соглашаемся на перезапуск служб
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
                    if response == '':
                        print("   🤖 Автоматический ответ: Enter (пустой ответ) для %s" % prompt_type)
                    else:
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
    
    def update_system(self, dry_run=False):
        """Обновление системы"""
        print("📦 Обновление системы...")
        
        if dry_run:
            print("⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
            print("✅ Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
            return True
        
        # Сначала обновляем списки пакетов
        print("\n🔄 Обновление списков пакетов...")
        update_cmd = ['apt-get', 'update']
        result = self.run_command_with_interactive_handling(update_cmd, dry_run)
        
        if result != 0:
            print("❌ Ошибка обновления списков пакетов")
            return False
        
        # Затем обновляем систему
        print("\n🚀 Обновление системы...")
        upgrade_cmd = ['apt-get', 'dist-upgrade', '-y']
        result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run)
        
        if result == 0:
            print("✅ Система успешно обновлена")
            
            # Автоматическая очистка ненужных пакетов
            print("\n🧹 Автоматическая очистка ненужных пакетов...")
            autoremove_cmd = ['apt-get', 'autoremove', '-y']
            autoremove_result = self.run_command_with_interactive_handling(autoremove_cmd, dry_run)
            
            if autoremove_result == 0:
                print("✅ Ненужные пакеты успешно удалены")
            else:
                print("⚠️ Предупреждение: не удалось удалить ненужные пакеты")
            
            return True
        else:
            print("❌ Ошибка обновления системы")
            return False
    
    def simulate_update_scenarios(self):
        """Симуляция различных сценариев обновления"""
        print("🧪 Симуляция сценариев обновления...")
        
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
        
        # Тест 2: перезапуск служб
        print("\n🔄 Тест 2: перезапуск служб")
        test_output = """Перезапустить службы во время пакетных операций? [Y/n]"""
        
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

def main():
    """Основная функция для тестирования"""
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("=" * 60)
    if dry_run:
        print("Тест модуля обновления системы (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля обновления системы")
    print("=" * 60)
    
    updater = SystemUpdater()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с системными пакетами")
        print("Запустите: sudo python system_updater.py")
        sys.exit(1)
    
    # Симулируем сценарии обновления
    updater.simulate_update_scenarios()
    
    # Тестируем обновление системы
    if not dry_run:
        print("\n🔧 Тест реального обновления системы...")
        success = updater.update_system(dry_run)
        
        if success:
            print("✅ Обновление системы завершено успешно")
        else:
            print("❌ Обновление системы завершено с ошибкой")
    else:
        print("\n⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется")
        updater.update_system(dry_run)
    
    if dry_run:
        print("\n✅ Тест модуля завершен! (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("\n✅ Тест модуля завершен!")

if __name__ == '__main__':
    main()
