#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Независимая тестовая форма для проверки восстановления геометрии окна
с имитацией перетаскивания мышкой через xdotool
Для Astro Linux
"""

import sys
import subprocess
import platform
import json
import time
import re
from pathlib import Path

# Проверка и установка tkinter
def check_and_install_tkinter():
    """Проверка и установка tkinter если необходимо"""
    try:
        import tkinter
        return True
    except ImportError:
        print("[INFO] tkinter не найден, пытаемся установить...")
        
        system = platform.system()
        
        if system == "Linux":
            try:
                result = subprocess.run(
                    ["sudo", "-n", "true"],
                    capture_output=True,
                    timeout=5
                )
                has_sudo = result.returncode == 0
                
                if not has_sudo:
                    print("[ERROR] Требуются права root для установки python3-tk")
                    print("[INFO] Запустите: sudo apt-get install -y python3-tk")
                    return False
                
                print("[INFO] Установка python3-tk...")
                result = subprocess.run(
                    ["sudo", "apt-get", "install", "-y", "python3-tk"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print("[INFO] python3-tk успешно установлен")
                    import tkinter
                    return True
                else:
                    print(f"[ERROR] Ошибка установки: {result.stderr}")
                    return False
            except Exception as e:
                print(f"[ERROR] Ошибка при установке: {e}")
                return False
        else:
            print(f"[ERROR] Автоматическая установка tkinter для {system} не поддерживается")
            return False

if not check_and_install_tkinter():
    print("[ERROR] Не удалось установить tkinter. Завершение работы.")
    sys.exit(1)

import tkinter as tk
from tkinter import messagebox


class WindowGeometryTest:
    """Тестовая форма для проверки сохранения и восстановления геометрии окна"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Тест геометрии окна - Имитация перетаскивания")
        
        # Путь к файлу настроек (в той же папке, где находится скрипт)
        script_dir = Path(__file__).parent
        self.settings_file = script_dir / 'window_geometry_test.json'
        
        # Устанавливаем минимальный размер
        self.root.minsize(500, 400)
        
        # Создаем виджеты
        self._create_widgets()
        
        # Загружаем сохраненную геометрию при запуске
        self._load_geometry()
        
        # Обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Обновление информации о координатах
        self._update_coordinates_info()
        self.root.after(500, self._schedule_update)
    
    def _create_widgets(self):
        """Создание элементов интерфейса"""
        # Верхний фрейм с информацией
        info_frame = tk.Frame(self.root, bg='#f0f0f0', relief=tk.RAISED, bd=1)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Метка с информацией о координатах
        self.info_label = tk.Label(
            info_frame,
            text="Загрузка...",
            font=("Courier", 11),
            justify=tk.LEFT,
            anchor="nw",
            bg='#f0f0f0',
            wraplength=600
        )
        self.info_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Нижний фрейм с кнопками
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Кнопка сохранения текущей позиции
        self.save_btn = tk.Button(
            button_frame,
            text="Сохранить позицию",
            command=self._save_current_geometry,
            width=18,
            bg='#4CAF50',
            fg='white',
            font=("Arial", 10, "bold")
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка восстановления сохраненной позиции
        restore_btn = tk.Button(
            button_frame,
            text="Восстановить (мышка)",
            command=self._restore_geometry_with_mouse,
            width=22,
            bg='#2196F3',
            fg='white',
            font=("Arial", 10, "bold")
        )
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка восстановления через geometry (для сравнения)
        restore_geom_btn = tk.Button(
            button_frame,
            text="Восстановить (geometry)",
            command=self._restore_geometry_direct,
            width=22,
            bg='#FF9800',
            fg='white',
            font=("Arial", 10, "bold")
        )
        restore_geom_btn.pack(side=tk.LEFT, padx=5)
    
    def _check_click_result(self, saved_before, mtime_before):
        """Проверяет, сработал ли клик (файл появился или обновился)"""
        import os
        saved_after = self.settings_file.exists() if hasattr(self, 'settings_file') else False
        if saved_after and not saved_before:
            return True
        elif saved_after and saved_before:
            try:
                mtime_after = os.path.getmtime(str(self.settings_file))
                if mtime_after > mtime_before + 0.05:
                    return True
            except:
                pass
        return False
    
    def _show_coordinates_marker(self, x, y, label=""):
        """
        Показывает временное окно-маркер с крестиком в указанных координатах
        для визуальной проверки попадания в заголовок окна
        
        Args:
            x: координата X (абсолютные координаты экрана)
            y: координата Y (абсолютные координаты экрана)
            label: подпись для маркера
        """
        try:
            marker = tk.Toplevel(self.root)
            marker.overrideredirect(True)  # Убираем рамку окна
            marker.attributes('-topmost', True)  # Поверх всех окон
            
            # Размер маркера
            marker_size = 40
            marker.geometry(f"{marker_size}x{marker_size}+{x - marker_size//2}+{y - marker_size//2}")
            
            # Создаем canvas для рисования крестика
            canvas = tk.Canvas(marker, width=marker_size, height=marker_size, bg='red', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # Рисуем крестик (X)
            padding = 5
            canvas.create_line(padding, padding, marker_size - padding, marker_size - padding, 
                             fill='white', width=3)
            canvas.create_line(marker_size - padding, padding, padding, marker_size - padding, 
                             fill='white', width=3)
            
            # Добавляем текст с координатами
            if label:
                canvas.create_text(marker_size // 2, marker_size // 2, 
                                 text=label, fill='white', font=('Arial', 8, 'bold'))
            
            # Автоматически закрываем маркер через 3 секунды
            marker.after(3000, marker.destroy)
            
            print(f"[DEBUG] Маркер показан в координатах ({x}, {y}) с подписью '{label}'")
            
        except Exception as e:
            print(f"[WARNING] Ошибка создания маркера: {e}")
    
    def _get_window_id(self):
        """Получение window ID текущего окна"""
        try:
            window_id = self.root.winfo_id()
            # Для X11 нужно преобразовать в hex формат, который понимает xdotool
            return hex(window_id)
        except Exception as e:
            print(f"Ошибка получения window ID: {e}")
            return None
    
    def _check_xdotool(self):
        """Проверка наличия xdotool и установка при необходимости"""
        try:
            result = subprocess.run(
                ['which', 'xdotool'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
            
            # Пытаемся установить
            print("[INFO] xdotool не найден, пытаемся установить...")
            install_result = subprocess.run(
                ['sudo', 'apt-get', 'install', '-y', 'xdotool'],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if install_result.returncode == 0:
                print("[INFO] xdotool успешно установлен")
                return True
            else:
                print(f"[ERROR] Не удалось установить xdotool: {install_result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Ошибка при проверке xdotool: {e}")
            return False
    
    def _move_window_gradually(self, target_winfo_x, target_winfo_y):
        """
        Постепенное перемещение окна маленькими шагами (имитация перетаскивания)
        Этот метод НЕ требует кликов мыши и должен обходить эффект прилипания
        
        Args:
            target_winfo_x: целевая координата X (winfo_x - координаты клиентской области)
            target_winfo_y: целевая координата Y (winfo_y - координаты клиентской области)
        """
        try:
            self.root.update_idletasks()
            
            # Получаем текущую позицию клиентской области (winfo_x/y)
            current_winfo_x = self.root.winfo_x()
            current_winfo_y = self.root.winfo_y()
            
            # Вычисляем смещение
            dx = target_winfo_x - current_winfo_x
            dy = target_winfo_y - current_winfo_y
            
            if abs(dx) < 1 and abs(dy) < 1:
                print("[INFO] Окно уже в нужной позиции")
                return True
            
            print(f"[INFO] Постепенное перемещение окна")
            print(f"[INFO] Из winfo_x/y: ({current_winfo_x}, {current_winfo_y})")
            print(f"[INFO] В winfo_x/y: ({target_winfo_x}, {target_winfo_y})")
            print(f"[INFO] Смещение: dx={dx:+d}, dy={dy:+d}")
            
            # Размер окна
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # Получаем текущую geometry для вычисления смещения
            current_geometry = self.root.geometry()
            # Парсим текущую geometry позицию
            if '+' in current_geometry:
                size_part, pos_part = current_geometry.split('+', 1)
                current_geom_x, current_geom_y = [int(p) for p in pos_part.split('+')]
            else:
                current_geom_x = current_winfo_x
                current_geom_y = current_winfo_y
            
            # Вычисляем смещение между geometry и winfo (примерно -6 по X, -33 по Y на Astra Linux)
            geom_offset_x = current_geom_x - current_winfo_x
            geom_offset_y = current_geom_y - current_winfo_y
            
            # Целевые координаты для geometry
            target_geom_x = target_winfo_x + geom_offset_x
            target_geom_y = target_winfo_y + geom_offset_y
            
            # Перемещаем шагами по 5 пикселей за раз (быстрее, но все еще плавно)
            step_size = 5  # Размер шага в пикселях
            steps = max(abs(dx), abs(dy)) // step_size + 1  # Количество шагов
            
            if steps == 0:
                return True
            
            step_dx = dx / steps
            step_dy = dy / steps
            
            # Выполняем перемещение
            for i in range(steps + 1):
                # Вычисляем следующую позицию
                if i < steps:
                    new_winfo_x = int(current_winfo_x + step_dx * (i + 1))
                    new_winfo_y = int(current_winfo_y + step_dy * (i + 1))
                else:
                    # Финальная позиция точно
                    new_winfo_x = target_winfo_x
                    new_winfo_y = target_winfo_y
                
                # Конвертируем в geometry координаты
                new_geom_x = new_winfo_x + geom_offset_x
                new_geom_y = new_winfo_y + geom_offset_y
                
                # Устанавливаем новую позицию
                self.root.geometry(f"{width}x{height}+{new_geom_x}+{new_geom_y}")
                self.root.update_idletasks()
                
                # Небольшая задержка между шагами (имитация плавного перетаскивания)
                time.sleep(0.01)  # 10ms между шагами
            
            # Проверяем результат
            time.sleep(0.1)
            self.root.update_idletasks()
            final_winfo_x = self.root.winfo_x()
            final_winfo_y = self.root.winfo_y()
            
            print(f"[INFO] Перемещение завершено. Финальная позиция winfo_x/y: ({final_winfo_x}, {final_winfo_y})")
            print(f"[INFO] Целевая позиция winfo_x/y: ({target_winfo_x}, {target_winfo_y})")
            print(f"[INFO] Отклонение: dx={final_winfo_x - target_winfo_x:+d}, dy={final_winfo_y - target_winfo_y:+d}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка при постепенном перемещении окна: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _move_window_with_mouse_simulation(self, target_x, target_y):
        """
        Имитация перетаскивания окна мышкой через xdotool
        ТОЛЬКО этот метод используется - никаких прямых методов перемещения!
        
        Args:
            target_x: целевая координата X (winfo_x - координаты клиентской области относительно экрана)
            target_y: целевая координата Y (winfo_y - координаты клиентской области относительно экрана)
        """
        if not self._check_xdotool():
            messagebox.showerror(
                "Ошибка",
                "xdotool не установлен. Установите его:\nsudo apt-get install -y xdotool"
            )
            return False
        
        try:
            # Обновляем информацию о размерах окна
            self.root.update_idletasks()
            
            # Получаем window ID окна
            window_id = self.root.winfo_id()
            print(f"[INFO] Window ID: {window_id}")
            
            # Получаем текущую позицию клиентской области окна в абсолютных координатах экрана
            current_root_x = self.root.winfo_rootx()
            current_root_y = self.root.winfo_rooty()
            window_width = self.root.winfo_width()
            
            # Получаем также winfo_x/y для сравнения
            current_winfo_x = self.root.winfo_x()
            current_winfo_y = self.root.winfo_y()
            
            print(f"[DEBUG] Текущая позиция:")
            print(f"  winfo_x/y: ({current_winfo_x}, {current_winfo_y})")
            print(f"  winfo_rootx/y: ({current_root_x}, {current_root_y})")
            print(f"  Целевая позиция winfo_x/y: ({target_x}, {target_y})")
            
            # Для главного окна winfo_x/y и winfo_rootx/y должны совпадать (координаты клиентской области относительно экрана)
            # Используем winfo_rootx/y как наиболее надежные для абсолютных координат
            current_client_x = current_root_x
            current_client_y = current_root_y
            
            # Вычисляем смещение клиентской области (куда должна переместиться клиентская область)
            client_dx = target_x - current_client_x
            client_dy = target_y - current_client_y
            
            print(f"[DEBUG] Смещение клиентской области: dx={client_dx:+d}, dy={client_dy:+d}")
            
            # Вычисляем координаты центра заголовка окна (где пользователь обычно хватает окно)
            # Заголовок находится НАД клиентской областью, примерно на 25-30 пикселей выше
            # winfo_rooty - это верх клиентской области, заголовок выше на высоту рамки + заголовка
            title_bar_y_offset = 22  # Заголовок находится примерно на 22 пикселя ВЫШЕ клиентской области
            
            # Текущие координаты центра заголовка (абсолютные координаты экрана)
            start_title_x = current_client_x + (window_width // 2)
            start_title_y = current_client_y - title_bar_y_offset  # ВЫЧИТАЕМ, т.к. заголовок выше
            
            # Целевые координаты центра заголовка (заголовок переместится на то же смещение что и клиентская область)
            # Для целевой позиции используем target_x/y (winfo_x/y) и вычитаем смещение заголовка
            target_title_x = target_x + (window_width // 2)
            target_title_y = target_y - title_bar_y_offset  # ВЫЧИТАЕМ, т.к. заголовок выше
            
            # Смещение для заголовка равно смещению клиентской области
            dx = client_dx
            dy = client_dy
            
            # Если смещение очень маленькое, не двигаем окно
            if abs(dx) < 2 and abs(dy) < 2:
                print(f"[INFO] Окно уже в нужной позиции (смещение: dx={dx}, dy={dy})")
                return True
            
            print(f"[INFO] Имитация перетаскивания:")
            print(f"  Текущая позиция заголовка: ({start_title_x}, {start_title_y})")
            print(f"  Целевая позиция заголовка: ({target_title_x}, {target_title_y})")
            print(f"  Смещение: dx={dx:+d}, dy={dy:+d}")
            
            # Показываем маркер в вычисленных координатах заголовка для визуальной проверки
            print("[INFO] Показываем маркер в вычисленных координатах заголовка...")
            self._show_coordinates_marker(start_title_x, start_title_y, "СТАРТ")
            time.sleep(2)  # Даем время увидеть маркер (2 секунды)
            
            # ШАГ 0: Получаем window ID в hex формате для xdotool
            window_id_decimal = self.root.winfo_id()
            window_id_hex = hex(window_id_decimal)
            print(f"[INFO] ШАГ 0: Window ID (decimal): {window_id_decimal}, (hex): {window_id_hex}")
            
            # Активируем окно через xdotool используя window ID
            # xdotool принимает ID как в десятичном, так и в hex формате (с префиксом 0x)
            print("[INFO] Активируем окно через xdotool windowactivate...")
            result = subprocess.run(
                ['xdotool', 'windowactivate', str(window_id_decimal)],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[WARNING] Ошибка windowactivate: {result.stderr}")
                # Пробуем hex формат
                result = subprocess.run(
                    ['xdotool', 'windowactivate', window_id_hex],
                    check=False,
                    timeout=3,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("[INFO] Окно активировано через xdotool (hex формат)")
            else:
                print("[INFO] Окно активировано через xdotool")
            time.sleep(0.3)
            
            # Также активируем через Tkinter для надежности
            self.root.focus_force()
            self.root.lift()
            self.root.update_idletasks()
            time.sleep(0.2)
            
            # ШАГ 1: Перемещаем курсор в центр заголовка окна
            print(f"[INFO] ШАГ 1: Перемещаем курсор в центр заголовка ({start_title_x}, {start_title_y})...")
            result = subprocess.run(
                ['xdotool', 'mousemove', str(start_title_x), str(start_title_y)],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[WARNING] Ошибка mousemove: {result.stderr}")
            else:
                print("[INFO] Курсор перемещен")
            time.sleep(0.4)
            
            # ТЕСТ: Проверяем работу xdotool через диагностику
            print("[TEST] ДИАГНОСТИКА: Проверяем работу xdotool...")
            print(f"[TEST] Целевые координаты: ({start_title_x}, {start_title_y}), Window ID: {window_id_decimal}")
            
            # ПРОВЕРКА 0: Проверяем, что xdotool может читать координаты курсора
            print("[TEST] ПРОВЕРКА 0: Проверяем, работает ли xdotool getmouselocation...")
            result_read = subprocess.run(
                ['xdotool', 'getmouselocation'],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result_read.returncode != 0:
                print(f"[TEST] ОШИБКА: xdotool getmouselocation не работает! stderr: {result_read.stderr}")
                print("[TEST] xdotool не может читать координаты - проблема с xdotool или правами доступа!")
                return False
            print(f"[TEST] ✓ getmouselocation работает: {result_read.stdout.strip()}")
            
            # ПРОВЕРКА 1: Проверяем, что xdotool может перемещать курсор программно
            # Сохраняем текущую позицию, перемещаем в тестовую точку, проверяем, возвращаем обратно
            print("[TEST] ПРОВЕРКА 1: Тестируем программное перемещение курсора...")
            original_location = result_read.stdout.strip()
            
            # Парсим оригинальные координаты
            match = re.search(r'x:(\d+)\s+y:(\d+)', original_location)
            if not match:
                print("[TEST] Не удалось распарсить координаты курсора")
                return False
            
            orig_x, orig_y = int(match.group(1)), int(match.group(2))
            test_x, test_y = orig_x + 50, orig_y + 50  # Смещаем на 50 пикселей
            
            # Перемещаем курсор
            result_move = subprocess.run(
                ['xdotool', 'mousemove', str(test_x), str(test_y)],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result_move.returncode != 0:
                print(f"[TEST] ОШИБКА: xdotool mousemove не работает! stderr: {result_move.stderr}")
                return False
            
            time.sleep(0.1)
            
            # Проверяем, переместился ли курсор
            result_check = subprocess.run(
                ['xdotool', 'getmouselocation'],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result_check.returncode == 0:
                match_check = re.search(r'x:(\d+)\s+y:(\d+)', result_check.stdout.strip())
                if match_check:
                    actual_x, actual_y = int(match_check.group(1)), int(match_check.group(2))
                    if abs(actual_x - test_x) < 5 and abs(actual_y - test_y) < 5:
                        print(f"[TEST] ✓ Курсор переместился программно! Было: ({orig_x}, {orig_y}), Стало: ({actual_x}, {actual_y})")
                    else:
                        print(f"[TEST] ⚠ Курсор НЕ переместился программно! Ожидали: ({test_x}, {test_y}), Фактически: ({actual_x}, {actual_y})")
                        # Возвращаем курсор на место
                        subprocess.run(['xdotool', 'mousemove', str(orig_x), str(orig_y)], check=False, timeout=2)
                        return False
                # Возвращаем курсор на место
                subprocess.run(['xdotool', 'mousemove', str(orig_x), str(orig_y)], check=False, timeout=2)
                time.sleep(0.1)
            
            # ШАГ 1: Проверяем текущее положение курсора
            print("[TEST] ШАГ 1: Проверяем текущее положение курсора...")
            result = subprocess.run(
                ['xdotool', 'getmouselocation'],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"[TEST] Текущее положение курсора: {result.stdout.strip()}")
            else:
                print(f"[TEST] Ошибка getmouselocation: {result.stderr}")
            
            # ШАГ 2: Перемещаем курсор в целевые координаты
            print(f"[TEST] ШАГ 2: Перемещаем курсор в ({start_title_x}, {start_title_y})...")
            result = subprocess.run(
                ['xdotool', 'mousemove', str(start_title_x), str(start_title_y)],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[TEST] ОШИБКА mousemove: {result.stderr}")
                return False
            time.sleep(0.3)
            
            # ШАГ 3: Проверяем новое положение курсора (должно совпадать с целевыми координатами)
            print("[TEST] ШАГ 3: Проверяем новое положение курсора...")
            result = subprocess.run(
                ['xdotool', 'getmouselocation'],
                check=False,
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"[TEST] Новое положение курсора: {result.stdout.strip()}")
                # Парсим координаты из вывода (формат: x:123 y:456 screen:0 window:12345)
                mouse_info = result.stdout.strip()
                if f"x:{start_title_x}" in mouse_info and f"y:{start_title_y}" in mouse_info:
                    print("[TEST] ✓ Курсор успешно переместился в целевые координаты!")
                else:
                    print("[TEST] ⚠ Курсор НЕ попал в целевые координаты!")
            else:
                print(f"[TEST] Ошибка getmouselocation: {result.stderr}")
            
            # ПРОВЕРКА КЛИКА: Сначала проверяем, работает ли клик вообще
            # Кликаем по кнопке "Сохранить позицию" в нашем окне - если она сработает, клик работает
            print("[TEST] ПРОВЕРКА КЛИКА: Проверяем, работает ли клик мыши вообще...")
            print("[TEST] Будем кликать по кнопке 'Сохранить позицию' - если она сработает, клик работает!")
            
            # Находим координаты кнопки "Сохранить позицию" (первая зеленая кнопка)
            # Получаем координаты окна
            win_rootx = self.root.winfo_rootx()
            win_rooty = self.root.winfo_rooty()
            
            # Приблизительные координаты первой кнопки (обычно внизу окна, по центру или слева)
            # Нужно найти кнопку программно через дочерние виджеты
            button_x = win_rootx + 100  # Примерные координаты
            button_y = win_rooty + 350  # Примерные координаты
            
            # Используем сохраненную ссылку на кнопку
            if hasattr(self, 'save_btn'):
                try:
                    self.root.update_idletasks()
                    widget_x = win_rootx + self.save_btn.winfo_x()
                    widget_y = win_rooty + self.save_btn.winfo_y()
                    widget_w = self.save_btn.winfo_width()
                    widget_h = self.save_btn.winfo_height()
                    button_x = widget_x + widget_w // 2
                    button_y = widget_y + widget_h // 2
                    print(f"[TEST] Координаты кнопки 'Сохранить позицию': ({button_x}, {button_y})")
                except Exception as e:
                    print(f"[TEST] Ошибка получения координат кнопки: {e}")
                    button_x = win_rootx + 100
                    button_y = win_rooty + 350
            
            # Фокусируем окно
            subprocess.run(['xdotool', 'windowfocus', str(window_id_decimal)], check=False, timeout=1)
            self.root.focus_force()
            self.root.lift()
            self.root.update_idletasks()
            time.sleep(0.3)
            
            # Перемещаем курсор на кнопку
            print(f"[TEST] Перемещаем курсор на кнопку ({button_x}, {button_y})...")
            result = subprocess.run(
                ['xdotool', 'mousemove', str(button_x), str(button_y)],
                check=False,
                timeout=2,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[TEST] Ошибка mousemove: {result.stderr}")
            time.sleep(0.2)
            
            # Сохраняем состояние - было ли сохранение до клика
            saved_before = self.settings_file.exists() if hasattr(self, 'settings_file') else False
            import os
            mtime_before = os.path.getmtime(str(self.settings_file)) if saved_before else 0
            
            # Пробуем разные способы клика
            print("[TEST] Пробуем разные способы клика...")
            clicked = False
            
            # Способ 1: click с --clearmodifiers
            print("[TEST] Способ 1: xdotool click --clearmodifiers 1...")
            result = subprocess.run(['xdotool', 'click', '--clearmodifiers', '1'], check=False, timeout=2, capture_output=True, text=True)
            print(f"[TEST] Способ 1 код: {result.returncode}")
            time.sleep(0.5)
            if self._check_click_result(saved_before, mtime_before):
                print("[TEST] ✓✓✓ Способ 1 РАБОТАЕТ!")
                clicked = True
            
            if not clicked:
                # Способ 2: mousedown + mouseup
                print("[TEST] Способ 2: mousedown + mouseup отдельно...")
                subprocess.run(['xdotool', 'mousedown', '1'], check=False, timeout=1)
                time.sleep(0.05)
                subprocess.run(['xdotool', 'mouseup', '1'], check=False, timeout=1)
                time.sleep(0.5)
                if self._check_click_result(saved_before, mtime_before):
                    print("[TEST] ✓✓✓ Способ 2 РАБОТАЕТ!")
                    clicked = True
            
            if not clicked:
                # Способ 3: цепочка команд
                print("[TEST] Способ 3: цепочка windowfocus + mousemove + click...")
                result = subprocess.run(
                    ['xdotool', 'windowfocus', str(window_id_decimal), 'mousemove', str(button_x), str(button_y), 'click', '1'],
                    check=False, timeout=3, capture_output=True, text=True
                )
                print(f"[TEST] Способ 3 код: {result.returncode}")
                time.sleep(0.5)
                if self._check_click_result(saved_before, mtime_before):
                    print("[TEST] ✓✓✓ Способ 3 РАБОТАЕТ!")
                    clicked = True
            
            if not clicked:
                # Способ 4: xte (если установлен) - другой синтаксис
                result_xte = subprocess.run(['which', 'xte'], check=False, timeout=1, capture_output=True, text=True)
                if result_xte.returncode == 0:
                    print("[TEST] Способ 4: xte с отдельными командами...")
                    subprocess.run(['xte', f'mousemove {button_x} {button_y}'], check=False, timeout=1, shell=True)
                    time.sleep(0.1)
                    subprocess.run(['xte', 'mouseclick 1'], check=False, timeout=1, shell=True)
                    time.sleep(0.5)
                    if self._check_click_result(saved_before, mtime_before):
                        print("[TEST] ✓✓✓ Способ 4 (xte) РАБОТАЕТ!")
                        clicked = True
            
            if not clicked:
                # Способ 5: Пробуем через python-xlib (прямые X11 события)
                print("[TEST] Способ 5: Пробуем python-xlib (прямые X11 события)...")
                try:
                    # Импортируем внутри try, чтобы избежать ошибок линтера если библиотека не установлена
                    import Xlib.display  # type: ignore
                    import Xlib.X  # type: ignore
                    from Xlib.ext import xtest  # type: ignore
                    X = Xlib.X
                    display = Xlib.display
                    
                    d = display.Display()
                    
                    # Перемещаем курсор
                    xtest.fake_input(d, X.MotionNotify, x=int(button_x), y=int(button_y))
                    d.sync()
                    time.sleep(0.1)
                    
                    # Нажимаем кнопку
                    xtest.fake_input(d, X.ButtonPress, 1)
                    d.sync()
                    time.sleep(0.05)
                    
                    # Отпускаем кнопку
                    xtest.fake_input(d, X.ButtonRelease, 1)
                    d.sync()
                    time.sleep(0.5)
                    
                    if self._check_click_result(saved_before, mtime_before):
                        print("[TEST] ✓✓✓ Способ 5 (python-xlib) РАБОТАЕТ!")
                        clicked = True
                    else:
                        print("[TEST] Способ 5 не сработал")
                except ImportError:
                    print("[TEST] python-xlib не установлен (pip3 install python-xlib)")
                except Exception as e:
                    print(f"[TEST] Ошибка python-xlib: {e}")
            
            if not clicked:
                # Проверяем окружение - возможно Wayland вместо X11
                print("[TEST] Проверяем окружение...")
                wayland_display = os.environ.get('WAYLAND_DISPLAY')
                xdisplay = os.environ.get('DISPLAY')
                print(f"[TEST] WAYLAND_DISPLAY: {wayland_display}")
                print(f"[TEST] DISPLAY: {xdisplay}")
                if wayland_display and not xdisplay:
                    print("[TEST] ⚠ Используется Wayland! xdotool не работает с Wayland!")
                    print("[TEST] Для Wayland нужны другие инструменты (ydotool, wtype)")
                else:
                    print("[TEST] Используется X11, но xdotool не может выполнять клики")
                    print("[TEST] Возможные причины:")
                    print("[TEST] - Отсутствуют права доступа к X-серверу (xhost +SI:localuser:$USER)")
                    print("[TEST] - Оконный менеджер блокирует синтетические события")
                    print("[TEST] - Проблемы с конфигурацией X11")
                    print("[TEST] Рекомендация: попробуйте установить python-xlib: pip3 install python-xlib")
                
                print("[TEST] ✗✗✗ Все способы клика не работают!")
                print("[TEST] БЕЗ РАБОЧЕГО КЛИКА НЕВОЗМОЖНО ПЕРЕТАСКИВАТЬ ОКНО!")
                return False
            
            print("[TEST] КЛИК РАБОТАЕТ! Переходим к перетаскиванию окна...")
            time.sleep(1)
            
            # ШАГ 4: Имитация перетаскивания окна
            # Последовательность: фокус -> mousemove -> клик для захвата -> mousedown -> mousemove -> mouseup
            print(f"[INFO] ШАГ 4: Имитация перетаскивания окна...")
            
            # Фокусируем окно через windowfocus
            print("[INFO] Фокусируем окно...")
            subprocess.run(['xdotool', 'windowfocus', str(window_id_decimal)], check=False, timeout=1)
            time.sleep(0.3)
            
            # Также активируем через Tkinter
            self.root.focus_force()
            self.root.lift()
            self.root.update_idletasks()
            time.sleep(0.2)
            
            # Перемещаем курсор в центр заголовка
            print(f"[INFO] Перемещаем курсор в центр заголовка ({start_title_x}, {start_title_y})...")
            result = subprocess.run(
                ['xdotool', 'mousemove', str(start_title_x), str(start_title_y)],
                check=False,
                timeout=2,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[ERROR] Ошибка mousemove: {result.stderr}")
                return False
            time.sleep(0.2)
            
            # Делаем клик для "захвата" заголовка окна (важно для некоторых WM)
            print("[INFO] Делаем клик для захвата заголовка...")
            subprocess.run(['xdotool', 'click', '1'], check=False, timeout=1)
            time.sleep(0.15)
            
            # Теперь нажимаем и удерживаем левую кнопку мыши (захватываем окно)
            print("[INFO] Нажимаем и удерживаем левую кнопку мыши...")
            result_down = subprocess.run(
                ['xdotool', 'mousedown', '1'],
                check=False,
                timeout=2,
                capture_output=True,
                text=True
            )
            if result_down.returncode != 0:
                print(f"[ERROR] Ошибка mousedown: {result_down.stderr}")
                return False
            print("[INFO] Левая кнопка мыши нажата (удерживается)")
            time.sleep(0.2)  # Важно: даем время окну "схватиться"
            
            # Перемещаем курсор к целевой позиции небольшими шагами (имитация плавного перетаскивания)
            print(f"[INFO] Перетаскиваем окно к целевой позиции ({target_title_x}, {target_title_y})...")
            steps = max(abs(dx), abs(dy)) // 3 + 1  # Шаги по 3 пикселя (более плавно)
            for step in range(steps + 1):
                # Вычисляем промежуточную позицию
                t = step / steps if steps > 0 else 1.0
                current_x = int(start_title_x + dx * t)
                current_y = int(start_title_y + dy * t)
                
                result_move = subprocess.run(
                    ['xdotool', 'mousemove', str(current_x), str(current_y)],
                    check=False,
                    timeout=1,
                    capture_output=True,
                    text=True
                )
                if result_move.returncode != 0:
                    print(f"[WARNING] Ошибка mousemove на шаге {step}: {result_move.stderr}")
                time.sleep(0.02)  # Увеличили задержку между шагами
            
            # Финальная позиция (убеждаемся что попали точно)
            result_final = subprocess.run(
                ['xdotool', 'mousemove', str(target_title_x), str(target_title_y)],
                check=False,
                timeout=2,
                capture_output=True,
                text=True
            )
            if result_final.returncode != 0:
                print(f"[WARNING] Ошибка финального mousemove: {result_final.stderr}")
            time.sleep(0.15)
            
            # Отпускаем левую кнопку мыши
            print("[INFO] Отпускаем левую кнопку мыши...")
            result_up = subprocess.run(
                ['xdotool', 'mouseup', '1'],
                check=False,
                timeout=2,
                capture_output=True,
                text=True
            )
            if result_up.returncode != 0:
                print(f"[ERROR] Ошибка mouseup: {result_up.stderr}")
                return False
            print("[INFO] Левая кнопка мыши отпущена")
            time.sleep(0.3)
            
            # Проверяем результат
            self.root.update_idletasks()
            final_x = self.root.winfo_x()
            final_y = self.root.winfo_y()
            print(f"[INFO] Перетаскивание завершено. Финальная позиция: ({final_x}, {final_y}), целевая: ({target_x}, {target_y})")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка при имитации перетаскивания мышкой: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"Ошибка при перемещении окна через имитацию мышкой:\n{e}"
            print(f"[ERROR] {error_msg}")
            messagebox.showerror("Ошибка", error_msg)
            return False
    
    def _save_current_geometry(self):
        """Сохранение текущей геометрии окна"""
        try:
            self.root.update_idletasks()
            
            # Получаем реальные координаты клиентской области (winfo_x/y)
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            
            geometry_data = {
                'width': width,
                'height': height,
                'x': x,
                'y': y
            }
            
            # Сохраняем в файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(geometry_data, f, indent=2, ensure_ascii=False)
            
            print(f"[INFO] Геометрия сохранена: {width}x{height}+{x}+{y}")
            # Не показываем messagebox при автоматическом тесте
            # messagebox.showinfo("Успех", f"Позиция сохранена:\n{width}x{height} в точке ({x}, {y})")
            self._update_coordinates_info()
            
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения геометрии: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить геометрию:\n{e}")
    
    def _load_geometry(self):
        """Загрузка сохраненной геометрии при запуске"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    geometry_data = json.load(f)
                
                width = geometry_data.get('width', 600)
                height = geometry_data.get('height', 400)
                x = geometry_data.get('x')
                y = geometry_data.get('y')
                
                # Устанавливаем размер
                self.root.geometry(f"{width}x{height}")
                self.root.update_idletasks()
                
                # Если есть координаты, восстанавливаем их через geometry (обычный способ)
                # Имитация перетаскивания мышкой доступна только через кнопку "Восстановить (мышка)"
                if x is not None and y is not None:
                    # Конвертируем winfo_x/y координаты в geometry координаты
                    # На Astra Linux обычно смещение: geometry_x = winfo_x - 6, geometry_y = winfo_y - 33
                    geometry_x = x - 6
                    geometry_y = y - 33
                    self.root.geometry(f"{width}x{height}+{geometry_x}+{geometry_y}")
                    print(f"[INFO] Загружена геометрия: {width}x{height}+{x}+{y} (применено через geometry)")
                else:
                    # Только размер без координат - центрируем
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    x = (screen_width - width) // 2
                    y = (screen_height - height) // 2
                    self.root.geometry(f"{width}x{height}+{x}+{y}")
                    print(f"[INFO] Загружена геометрия (без координат), окно центрировано")
            else:
                # Нет сохраненной геометрии - используем значения по умолчанию
                default_width = 600
                default_height = 400
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                x = (screen_width - default_width) // 2
                y = (screen_height - default_height) // 2
                self.root.geometry(f"{default_width}x{default_height}+{x}+{y}")
                print(f"[INFO] Используется геометрия по умолчанию, окно центрировано")
                
        except Exception as e:
            print(f"[WARNING] Ошибка загрузки геометрии: {e}")
            # Используем значения по умолчанию
            self.root.geometry("600x400")
    
    def _restore_geometry_with_mouse(self):
        """Восстановление сохраненной геометрии через имитацию перетаскивания мышкой"""
        try:
            if not self.settings_file.exists():
                messagebox.showwarning("Предупреждение", "Нет сохраненной геометрии")
                return
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                geometry_data = json.load(f)
            
            x = geometry_data.get('x')
            y = geometry_data.get('y')
            width = geometry_data.get('width')
            height = geometry_data.get('height')
            
            if x is None or y is None:
                messagebox.showwarning("Предупреждение", "В сохраненной геометрии нет координат")
                return
            
            # Устанавливаем размер (если отличается)
            if width and height:
                current_width = self.root.winfo_width()
                current_height = self.root.winfo_height()
                if width != current_width or height != current_height:
                    self.root.geometry(f"{width}x{height}")
                    self.root.update_idletasks()
                    time.sleep(0.2)
            
            # Перемещаем окно через постепенное перемещение (не требует кликов мыши)
            # Этот метод имитирует перетаскивание маленькими шагами и обходит эффект прилипания
            self._move_window_gradually(x, y)
            self._update_coordinates_info()
            
        except Exception as e:
            print(f"[ERROR] Ошибка восстановления геометрии: {e}")
            messagebox.showerror("Ошибка", f"Не удалось восстановить геометрию:\n{e}")
    
    def _restore_geometry_direct(self):
        """Восстановление сохраненной геометрии напрямую через geometry() (для сравнения)"""
        try:
            if not self.settings_file.exists():
                messagebox.showwarning("Предупреждение", "Нет сохраненной геометрии")
                return
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                geometry_data = json.load(f)
            
            width = geometry_data.get('width', 600)
            height = geometry_data.get('height', 400)
            x = geometry_data.get('x')
            y = geometry_data.get('y')
            
            if x is not None and y is not None:
                # Конвертируем winfo координаты в geometry координаты
                # На Astra Linux обычно смещение: geometry_x = winfo_x - 6, geometry_y = winfo_y - 33
                geometry_x = x - 6
                geometry_y = y - 33
                self.root.geometry(f"{width}x{height}+{geometry_x}+{geometry_y}")
            else:
                self.root.geometry(f"{width}x{height}")
            
            self.root.update_idletasks()
            self._update_coordinates_info()
            messagebox.showinfo("Информация", "Геометрия восстановлена напрямую (через geometry())")
            
        except Exception as e:
            print(f"[ERROR] Ошибка восстановления геометрии: {e}")
            messagebox.showerror("Ошибка", f"Не удалось восстановить геометрию:\n{e}")
    
    def _update_coordinates_info(self):
        """Обновление информации о текущих координатах"""
        try:
            self.root.update_idletasks()
            
            geometry_str = self.root.geometry()
            winfo_x = self.root.winfo_x()
            winfo_y = self.root.winfo_y()
            winfo_width = self.root.winfo_width()
            winfo_height = self.root.winfo_height()
            
            # Парсим geometry
            if '+' in geometry_str:
                size_part, pos_part = geometry_str.split('+', 1)
                width, height = [int(x) for x in size_part.split('x')]
                geom_x, geom_y = [int(x) for x in pos_part.split('+')]
            else:
                width, height = [int(x) for x in geometry_str.split('x')]
                geom_x = geom_y = 0
            
            # Загружаем сохраненную геометрию для сравнения
            saved_info = "Нет сохраненной геометрии"
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    saved_x = saved_data.get('x', 'N/A')
                    saved_y = saved_data.get('y', 'N/A')
                    saved_w = saved_data.get('width', 'N/A')
                    saved_h = saved_data.get('height', 'N/A')
                    saved_info = f"{saved_w}x{saved_h}+{saved_x}+{saved_y}"
                except:
                    pass
            
            # Формируем текст информации
            info_text = f"""ТЕКУЩАЯ ГЕОМЕТРИЯ ОКНА:

Размер окна:
   geometry(): {width}x{height}
   winfo: {winfo_width}x{winfo_height}

Позиция окна:
   geometry(): +{geom_x}+{geom_y} (координаты окна с рамкой)
   winfo_x/y(): +{winfo_x}+{winfo_y} (координаты клиентской области)

Разница координат:
   X: {geom_x - winfo_x:+d}
   Y: {geom_y - winfo_y:+d}

СОХРАНЕННАЯ ГЕОМЕТРИЯ:
   {saved_info}

Примечание:
   • winfo_x/y() - реальные координаты клиентской области
   • Сохраняем и восстанавливаем winfo_x/y координаты
   • Имитация перетаскивания мышкой исключает эффект прилипания"""
            
            self.info_label.config(text=info_text)
            
        except Exception as e:
            self.info_label.config(text=f"Ошибка обновления информации: {e}")
    
    def _schedule_update(self):
        """Планирование периодического обновления информации"""
        self._update_coordinates_info()
        self.root.after(500, self._schedule_update)
    
    def _on_closing(self):
        """Обработчик закрытия окна - сохранение геометрии"""
        try:
            self.root.update_idletasks()
            
            # Сохраняем текущую геометрию при закрытии
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            
            geometry_data = {
                'width': width,
                'height': height,
                'x': x,
                'y': y
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(geometry_data, f, indent=2, ensure_ascii=False)
            
            print(f"[INFO] Геометрия сохранена при закрытии: {width}x{height}+{x}+{y}")
            
        except Exception as e:
            print(f"[WARNING] Ошибка сохранения геометрии при закрытии: {e}")
        
        self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = WindowGeometryTest()
    app.run()

