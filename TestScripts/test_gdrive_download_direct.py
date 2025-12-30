#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для прямой проверки скачивания из Google Drive с детальным логированием
Версия: V3.7.210 (2025.12.31)
Компания: ООО "НПА Вира-Реалтайм"
"""

import sys
import os
import re
import io
import tempfile
import requests
from urllib.parse import urlencode

def test_direct_download(file_id, file_name):
    """Прямое тестирование скачивания файла с детальным логированием"""
    
    print("=" * 80)
    print(f"ПРЯМОЕ ТЕСТИРОВАНИЕ СКАЧИВАНИЯ: {file_name}")
    print("=" * 80)
    print(f"[STEP 1] File ID: {file_id}")
    print(f"[STEP 1] File Name: {file_name}\n")
    
    # Шаг 1: Прямая ссылка
    file_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"[STEP 2] Прямая ссылка: {file_url}\n")
    
    session = requests.Session()
    
    # Добавляем заголовки браузера для имитации реального браузера
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    # Шаг 2: Пробуем получить страницу
    print("[STEP 3] Отправляем GET запрос на прямую ссылку...")
    try:
        response = session.get(file_url, timeout=30)
        print(f"[STEP 3] Статус код: {response.status_code}")
        print(f"[STEP 3] Content-Type: {response.headers.get('content-type', 'не указан')}")
        print(f"[STEP 3] Content-Length: {response.headers.get('content-length', 'не указан')}\n")
        
        html_content = response.text
        print(f"[STEP 3] Размер HTML: {len(html_content)} байт")
        print(f"[STEP 3] Первые 500 символов HTML:\n{html_content[:500]}\n")
        
        # Проверяем, не ошибка ли "Too many users"
        if 'too many users' in html_content.lower() or 'просматривали или скачивали слишком часто' in html_content.lower():
            print("[ERROR] Обнаружена ошибка 'Too many users'")
            return None, False
        
        # Проверяем, не страница ли подтверждения вируса
        is_virus_confirmation = False
        if 'не удалось проверить файл на наличие вирусов' in html_content.lower() or \
           'не удалось проверить' in html_content.lower() and 'вирус' in html_content.lower() or \
           'все равно скачать' in html_content.lower() or \
           'download anyway' in html_content.lower():
            is_virus_confirmation = True
            print("[STEP 4] Обнаружена страница подтверждения вируса\n")
        
        # Шаг 3: Ищем форму
        print("[STEP 5] Ищем форму подтверждения...")
        form_action_match = re.search(r'<form[^>]*action="(https://drive\.usercontent\.google\.com/download[^"]*)"', html_content, re.IGNORECASE)
        
        if not form_action_match:
            print("[ERROR] Форма не найдена!")
            return None, False
        
        form_action = form_action_match.group(1)
        print(f"[STEP 5] Form Action: {form_action}\n")
        
        # Определяем метод формы
        form_method_match = re.search(r'<form[^>]*method=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        form_method = form_method_match.group(1).lower() if form_method_match else 'get'
        print(f"[STEP 6] Form Method: {form_method}\n")
        
        # Извлекаем скрытые поля
        print("[STEP 7] Извлекаем скрытые поля формы...")
        form_data = {}
        # Ищем все скрытые поля (более гибкий паттерн)
        hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        for name, value in hidden_inputs:
            form_data[name] = value
            print(f"[STEP 7]   {name} = {value}")
        
        # Также ищем параметр 'at' отдельно (может быть в другом формате)
        at_patterns = [
            r'name=["\']at["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*name=["\']at["\'][^>]*value=["\']([^"\']+)["\']',
        ]
        for pattern in at_patterns:
            at_match = re.search(pattern, html_content, re.IGNORECASE)
            if at_match and 'at' not in form_data:
                form_data['at'] = at_match.group(1)
                print(f"[STEP 7]   at = {form_data['at']} (найден через дополнительный поиск)")
                break
        
        print()
        
        # Проверяем, все ли нужные поля есть
        required_fields = ['id', 'export', 'confirm']
        missing_fields = [f for f in required_fields if f not in form_data]
        if missing_fields:
            print(f"[WARNING] Отсутствуют обязательные поля: {missing_fields}")
        else:
            print("[STEP 7] Все обязательные поля найдены ✓")
        
        # Проверяем cookies
        print(f"[STEP 7] Cookies в сессии: {len(session.cookies)} шт.")
        if session.cookies:
            print(f"[STEP 7] Cookie names: {list(session.cookies.keys())}")
        print()
        
        # Шаг 4: Обрабатываем форму
        if form_method == 'get':
            print("[STEP 8] Обрабатываем GET форму...")
            params = urlencode(form_data)
            download_url_get = f"{form_action}?{params}"
            print(f"[STEP 8] Полный URL для скачивания: {download_url_get}")
            print(f"[STEP 8] Параметры: {form_data}\n")
            
            # Также пробуем альтернативный URL через drive.google.com
            alt_url = f"https://drive.google.com/uc?export=download&id={form_data.get('id')}&confirm={form_data.get('confirm', 't')}"
            print(f"[STEP 8] Альтернативный URL: {alt_url}\n")
            
            print("[STEP 9] Отправляем GET запрос для скачивания файла...")
            print(f"[STEP 9] Cookies перед запросом: {dict(session.cookies)}")
            print(f"[STEP 9] Headers: {dict(session.headers)}\n")
            response = session.get(download_url_get, stream=True, timeout=30, allow_redirects=True)
            
            print(f"[STEP 9] Статус код: {response.status_code}")
            print(f"[STEP 9] Content-Type: {response.headers.get('content-type', 'не указан')}")
            print(f"[STEP 9] Content-Length: {response.headers.get('content-length', 'не указан')}")
            
            # Проверяем первые байты
            peek = response.raw.read(512)
            try:
                response.raw.seek(0)
            except (AttributeError, io.UnsupportedOperation):
                print("[WARNING] Не удалось вернуться в начало потока, создаем новый запрос...")
                response = session.get(download_url_get, stream=True, timeout=30, allow_redirects=True)
                peek = response.raw.read(512)
                try:
                    response.raw.seek(0)
                except (AttributeError, io.UnsupportedOperation):
                    pass
            
            peek_str = peek.decode('utf-8', errors='ignore').lower()
            print(f"[STEP 9] Первые 100 символов ответа: {peek_str[:100]}\n")
            
            content_type = response.headers.get('content-type', '').lower()
            is_html = 'text/html' in content_type or '<html' in peek_str or '<!doctype' in peek_str
            
            if is_html:
                print("[ERROR] Получен HTML вместо файла!")
                html_content_error = response.text
                print(f"[ERROR] HTML содержимое (первые 1000 символов):\n{html_content_error[:1000]}\n")
                
                # Проверяем, может быть это другая форма подтверждения
                if 'quota exceeded' in html_content_error.lower():
                    print("[INFO] Обнаружена ошибка 'quota exceeded'")
                    print("[INFO] Это может быть временное ограничение Google Drive")
                    print("[INFO] Попробуйте позже или проверьте в браузере\n")
                elif 'virus' in html_content_error.lower() or 'вирус' in html_content_error.lower():
                    print("[INFO] Обнаружена еще одна страница подтверждения вируса")
                    print("[INFO] Попробуем обработать её...\n")
                    # Рекурсивно вызываем обработку
                    return test_direct_download(file_id, file_name)
                
                return None, False
            else:
                print("[STEP 10] Получен файл! Начинаем скачивание...\n")
                
                # Создаем временный файл
                temp_dir = tempfile.mkdtemp(prefix='gdrive_test_')
                final_path = os.path.join(temp_dir, file_name)
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                print(f"[STEP 11] Сохраняем в: {final_path}")
                if total_size > 0:
                    print(f"[STEP 11] Ожидаемый размер: {total_size / 1024 / 1024:.2f} МБ\n")
                
                with open(final_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Показываем прогресс каждые 10 МБ
                            if total_size > 0 and downloaded % (10 * 1024 * 1024) < 8192:
                                progress = (downloaded / total_size) * 100
                                print(f"[STEP 11] Прогресс: {progress:.1f}% ({downloaded / 1024 / 1024:.1f} МБ / {total_size / 1024 / 1024:.1f} МБ)")
                
                if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                    file_size = os.path.getsize(final_path)
                    print(f"\n[OK] Файл успешно скачан!")
                    print(f"[OK] Путь: {final_path}")
                    print(f"[OK] Размер: {file_size:,} байт ({file_size / 1024 / 1024:.2f} МБ)")
                    return final_path, True
                else:
                    print("\n[ERROR] Файл не был скачан или имеет нулевой размер")
                    return None, False
        else:
            print("[ERROR] POST форма пока не реализована в тесте")
            return None, False
            
    except Exception as e:
        print(f"\n[ERROR] Исключение: {e}")
        import traceback
        traceback.print_exc()
        return None, False

def main():
    """Тестирование одного файла (AstraPack.tar.gz)"""
    
    # Тестируем AstraPack.tar.gz (самый большой файл)
    file_id = '1s3lX1fcqai4DeNe8XOhMDffYZuSbfEin'
    file_name = 'AstraPack.tar.gz'
    
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ПРЯМОГО СКАЧИВАНИЯ ИЗ GOOGLE DRIVE")
    print("=" * 80)
    print("\nТестируем файл: AstraPack.tar.gz")
    print("Это самый большой файл (8GB), требует подтверждения\n")
    
    result = test_direct_download(file_id, file_name)
    
    if result[1]:
        print("\n" + "=" * 80)
        print("✓ ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("✗ ТЕСТ НЕ ПРОЙДЕН")
        print("=" * 80)
        sys.exit(1)

if __name__ == '__main__':
    main()

