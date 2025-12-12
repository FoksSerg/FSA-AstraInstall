#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI-приложение для автоматизации Find & Replace в Cursor
Версия: 1.0.0
Дата: 2025.12.11
Компания: ООО "НПА Вира-Реалтайм"
"""

import tkinter as tk
from tkinter import ttk
import pyperclip
import time
import subprocess
import json
import os

try:
    import pyautogui  # type: ignore
    PY_AUTOGUI_AVAILABLE = True
except ImportError:
    PY_AUTOGUI_AVAILABLE = False
    print("⚠️ pyautogui не установлен. Установите: pip3 install pyautogui")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL/Pillow не установлен. Установите: pip3 install Pillow")

class FindReplaceHelper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Find & Replace Helper для Cursor")
        
        # Путь к файлу настроек (рядом с скриптом)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings_file = os.path.join(script_dir, '.find_replace_helper_settings.json')
        
        # Загружаем сохранённые настройки окна
        window_settings = self.load_window_settings()
        
        # Окно поверх всех окон
        self.root.attributes('-topmost', True)
        
        # Устанавливаем размер и позицию из настроек или по умолчанию
        if window_settings:
            geometry = f"{window_settings['width']}x{window_settings['height']}+{window_settings['x']}+{window_settings['y']}"
            self.root.geometry(geometry)
            self.root.resizable(True, True)  # Разрешаем изменение размеров
        else:
            # Позиционируем окно в зоне редактирования (справа вверху) по умолчанию
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            window_width = 600
            window_height = 400
            x = screen_width - window_width - 50  # 50px отступ от правого края
            y = 100  # 100px от верхнего края
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.root.resizable(True, True)  # Разрешаем изменение размеров
        
        # Переменные
        self.old_text = tk.StringVar()
        self.new_text = tk.StringVar()
        self.copy_mode = "old"  # "old" или "new"
        
        # Координаты маркера для клика
        self.marker_x = None
        self.marker_y = None
        self.marker_window = None
        
        # Координаты области проверки "No results" (настраиваемая рамка)
        self.check_area_x = None
        self.check_area_y = None
        self.check_area_width = 200
        self.check_area_height = 40
        self.check_area_window = None
        
        # Загружаем сохранённые настройки маркера и области проверки
        self.load_marker_and_area_settings()
        
        self.create_widgets()
        
        # Привязываем обработчики для сохранения размера и позиции
        self.root.bind('<Configure>', self.on_window_configure)
        
        # КРИТИЧНО: Обработчик для сохранения фокуса на главном окне
        self.root.bind('<FocusIn>', self.on_root_focus_in)
        
        # Сохраняем настройки при закрытии окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Открываем маркер сразу при запуске
        self.create_draggable_marker()
    
    def create_widgets(self):
        # Заголовок
        title_label = tk.Label(self.root, text="Find & Replace Helper", 
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Поле "Старый текст"
        old_frame = tk.Frame(self.root)
        old_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(old_frame, text="Старый текст (Find):").pack(anchor=tk.W)
        old_entry = tk.Text(old_frame, height=5, wrap=tk.WORD)
        old_entry.pack(fill=tk.X, pady=5)
        # Добавляем поддержку стандартных горячих клавиш для вставки
        def paste_text(event):
            try:
                text = self.root.clipboard_get()
                old_entry.insert(tk.INSERT, text)
                return "break"
            except:
                return "break"
        old_entry.bind('<Control-v>', paste_text)
        old_entry.bind('<Command-v>', paste_text)
        self.old_entry = old_entry
        
        # Кнопка "Копировать из буфера" для старого текста
        old_copy_btn = tk.Button(old_frame, text="📋 Копировать из буфера → Старый текст",
                                command=lambda: self.copy_from_clipboard("old", old_entry))
        old_copy_btn.pack(fill=tk.X, pady=2)
        
        # Поле "Новый текст"
        new_frame = tk.Frame(self.root)
        new_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(new_frame, text="Новый текст (Replace):").pack(anchor=tk.W)
        new_entry = tk.Text(new_frame, height=5, wrap=tk.WORD)
        new_entry.pack(fill=tk.X, pady=5)
        # Добавляем поддержку стандартных горячих клавиш для вставки
        def paste_text_new(event):
            try:
                text = self.root.clipboard_get()
                new_entry.insert(tk.INSERT, text)
                return "break"
            except:
                return "break"
        new_entry.bind('<Control-v>', paste_text_new)
        new_entry.bind('<Command-v>', paste_text_new)
        self.new_entry = new_entry
        
        # Кнопка "Копировать из буфера" для нового текста
        new_copy_btn = tk.Button(new_frame, text="📋 Копировать из буфера → Новый текст",
                                command=lambda: self.copy_from_clipboard("new", new_entry))
        new_copy_btn.pack(fill=tk.X, pady=2)
        
        # Кнопки управления
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        apply_btn = tk.Button(button_frame, text="✅ Применить в Cursor", 
                             command=self.apply_replace, bg="#4CAF50", fg="black",
                             font=("Arial", 10, "bold"))
        apply_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        clear_btn = tk.Button(button_frame, text="🗑 Очистить", 
                             command=self.clear_fields, bg="#f44336", fg="black")
        clear_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Кнопка для отладки - получение всех элементов
        debug_btn = tk.Button(button_frame, text="🔍 Показать элементы", 
                             command=self.get_all_elements, bg="#2196F3", fg="black")
        debug_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Кнопка для настройки области проверки "No results"
        area_btn = tk.Button(button_frame, text="📐 Настроить область", 
                             command=self.create_check_area_editor, bg="#FF9800", fg="black")
        area_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Инструкция
        info_label = tk.Label(self.root, 
                             text="💡 Инструкция:\n1. Скопируйте старый текст в буфер\n2. Нажмите 'Копировать из буфера → Старый текст'\n3. Скопируйте новый текст в буфер\n4. Нажмите 'Копировать из буфера → Новый текст'\n5. Нажмите 'Применить в Cursor'\n6. В Cursor откроется Find & Replace (Ctrl+H) с заполненными полями",
                             font=("Arial", 9), justify=tk.LEFT, fg="gray")
        info_label.pack(pady=10)
    
    def copy_from_clipboard(self, mode, entry_widget):
        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                entry_widget.delete("1.0", tk.END)
                entry_widget.insert("1.0", clipboard_text)
                if mode == "old":
                    self.old_text.set(clipboard_text)
                else:
                    self.new_text.set(clipboard_text)
        except Exception as e:
            pass
    
    def click_with_applescript(self, x, y):
        """Выполняет клик через AppleScript (более надёжно на macOS)
        Координаты должны быть абсолютными (относительно экрана)"""
        print(f"[DEBUG] Выполнение клика через AppleScript в точке: ({x}, {y})")
        try:
            script = f'''
            tell application "Cursor"
                activate
            end tell
            delay 0.2
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    click at {{{x}, {y}}}
                end tell
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            print(f"[DEBUG] AppleScript клик выполнен, код возврата: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Ошибка AppleScript: {result.stderr}")
            if result.stdout:
                print(f"[DEBUG] Вывод AppleScript: {result.stdout}")
            return result.returncode == 0
        except Exception as e:
            print(f"[DEBUG] Ошибка при выполнении клика через AppleScript: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def activate_cursor_window(self):
        """Активирует окно Cursor"""
        try:
            script = '''
            tell application "Cursor"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
        except Exception:
            pass
    
    def get_focused_element_bounds(self):
        """Получает координаты и размеры элемента с фокусом (поле Find)"""
        try:
            # Пробуем несколько способов поиска элемента с фокусом
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    set focusedElement to missing value
                    
                    -- Способ 1: Ищем text field с фокусом
                    try
                        set windowsList to every window
                        repeat with win in windowsList
                            try
                                set textFields to every text field of win
                                repeat with tf in textFields
                                    try
                                        if focused of tf is true then
                                            set focusedElement to tf
                                            exit repeat
                                        end if
                                    end try
                                end repeat
                                if focusedElement is not missing value then exit repeat
                            end try
                        end repeat
                    end try
                    
                    -- Способ 2: Если не нашли, ищем любой элемент с фокусом
                    if focusedElement is missing value then
                        try
                            repeat with win in windowsList
                                try
                                    set uiElements to every UI element of win
                                    repeat with elem in uiElements
                                        try
                                            if focused of elem is true then
                                                set elemRole to role of elem
                                                -- Ищем text field или text area
                                                if elemRole is "AXTextField" or elemRole is "AXTextArea" then
                                                    set focusedElement to elem
                                                    exit repeat
                                                end if
                                            end if
                                        end try
                                    end repeat
                                    if focusedElement is not missing value then exit repeat
                                end try
                            end repeat
                        end try
                    end if
                    
                    -- Получаем bounds
                    if focusedElement is not missing value then
                        try
                            set {x, y} to position of focusedElement
                            set {width, height} to size of focusedElement
                            return x & "," & y & "," & width & "," & height
                        on error
                            return "ERROR:Не удалось получить position/size"
                        end try
                    else
                        return "NOT_FOUND"
                    end if
                end tell
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                output = result.stdout.strip()
                if output == "NOT_FOUND" or output.startswith("ERROR"):
                    print(f"⚠️ Не удалось получить bounds элемента с фокусом: {output}")
                    return None
                parts = output.split(',')
                if len(parts) == 4:
                    return {
                        'x': int(parts[0]),
                        'y': int(parts[1]),
                        'width': int(parts[2]),
                        'height': int(parts[3])
                    }
            return None
        except Exception as e:
            print(f"⚠️ Ошибка при получении bounds: {e}")
            return None
    
    def show_check_area(self, x, y, width, height):
        """Показывает рамку вокруг области проверки для визуализации"""
        try:
            marker = tk.Toplevel()
            marker.overrideredirect(True)
            marker.attributes('-topmost', True)
            marker.attributes('-alpha', 0.3)
            
            # Рамка красного цвета
            canvas = tk.Canvas(marker, width=width+4, height=height+4, 
                             highlightthickness=0, bg='red')
            canvas.pack()
            # Внутренняя прозрачная область
            canvas.create_rectangle(2, 2, width+2, height+2, 
                                  outline='red', width=2, fill='')
            
            marker.geometry(f"{width+4}x{height+4}+{x-2}+{y-2}")
            
            # Закрываем через 3 секунды
            marker.after(3000, marker.destroy)
            
            return marker
        except Exception as e:
            print(f"⚠️ Ошибка при создании рамки: {e}")
            return None
    
    def create_check_area_editor(self):
        """Создаёт настраиваемую рамку для области проверки 'No results'"""
        if self.check_area_window and self.check_area_window.winfo_exists():
            self.check_area_window.lift()
            return
        
        # Создаём окно с рамкой
        area_window = tk.Toplevel(self.root)
        area_window.overrideredirect(True)
        area_window.attributes('-alpha', 0.55)  # Полупрозрачное окно
        # По умолчанию окно НЕ поверх всех окон, чтобы не блокировать главное окно
        area_window.attributes('-topmost', False)
        # КРИТИЧНО: Окно области НЕ должно перехватывать фокус
        area_window.takefocus = False
        area_window.focus_set = lambda: None  # Отключаем установку фокуса
        # События не привязаны по умолчанию - окно неактивно и не перехватывает клики
        
        # Начальные координаты
        if self.check_area_x is None or self.check_area_y is None:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            initial_x = screen_width // 2 - self.check_area_width // 2
            initial_y = screen_height // 2 - self.check_area_height // 2
        else:
            initial_x = self.check_area_x - 10
            initial_y = self.check_area_y - 10
        
        # Canvas для рамки с видимым фоном
        canvas = tk.Canvas(area_window, width=self.check_area_width+20, 
                          height=self.check_area_height+20, 
                          highlightthickness=0, bg='#FFE0E0', cursor='fleur', takefocus=0)  # Светло-красный фон, без фокуса
        canvas.pack()
        
        # Рисуем рамку
        canvas.create_rectangle(10, 10, self.check_area_width+10, self.check_area_height+10, 
                              outline='red', width=3, fill='', dash=(5, 5))
        canvas.create_text(self.check_area_width//2+10, self.check_area_height//2+10, 
                          text="Область\nпроверки", font=('Arial', 10, 'bold'), 
                          fill='red', justify=tk.CENTER)
        
        # Рисуем маркеры для изменения размеров (большие видимые квадратики по углам)
        resize_handle_size = 12
        handles = [
            (10, 10),  # Левый верхний
            (self.check_area_width+10, 10),  # Правый верхний
            (10, self.check_area_height+10),  # Левый нижний
            (self.check_area_width+10, self.check_area_height+10)  # Правый нижний
        ]
        for hx, hy in handles:
            # Внешний квадрат
            canvas.create_rectangle(hx-resize_handle_size//2, hy-resize_handle_size//2,
                                  hx+resize_handle_size//2, hy+resize_handle_size//2,
                                  outline='red', fill='red', width=3)
            # Внутренний белый квадрат для контраста
            canvas.create_rectangle(hx-resize_handle_size//2+2, hy-resize_handle_size//2+2,
                                  hx+resize_handle_size//2-2, hy+resize_handle_size//2-2,
                                  outline='white', fill='white', width=1)
        
        area_window.geometry(f"{self.check_area_width+20}x{self.check_area_height+20}+{initial_x}+{initial_y}")
        self.check_area_window = area_window
        
        # Переменные для перетаскивания и изменения размеров
        self.area_drag_start_x = 0
        self.area_drag_start_y = 0
        self.area_resize_mode = None  # 'move', 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'
        self.area_start_width = self.check_area_width
        self.area_start_height = self.check_area_height
        self.area_start_x = initial_x
        self.area_start_y = initial_y
        
        def get_resize_mode(x, y):
            """Определяет режим изменения размеров по координатам"""
            handle_size = resize_handle_size + 10  # Увеличиваем зону захвата
            if x < handle_size and y < handle_size:
                return 'nw'  # Северо-запад
            elif x > self.check_area_width+10-handle_size and y < handle_size:
                return 'ne'  # Северо-восток
            elif x < handle_size and y > self.check_area_height+10-handle_size:
                return 'sw'  # Юго-запад
            elif x > self.check_area_width+10-handle_size and y > self.check_area_height+10-handle_size:
                return 'se'  # Юго-восток
            elif y < handle_size:
                return 'n'  # Север
            elif y > self.check_area_height+10-handle_size:
                return 's'  # Юг
            elif x < handle_size:
                return 'w'  # Запад
            elif x > self.check_area_width+10-handle_size:
                return 'e'  # Восток
            else:
                return 'move'  # Перемещение
        
        def update_cursor(event):
            """Обновляет курсор при наведении"""
            mode = get_resize_mode(event.x, event.y)
            cursors = {
                'nw': 'top_left_corner', 'ne': 'top_right_corner',
                'sw': 'bottom_left_corner', 'se': 'bottom_right_corner',
                'n': 'top_side', 's': 'bottom_side',
                'e': 'right_side', 'w': 'left_side',
                'move': 'fleur'
            }
            canvas.config(cursor=cursors.get(mode, 'fleur'))
        
        def start_drag(event):
            self.area_drag_start_x = event.x
            self.area_drag_start_y = event.y
            self.area_resize_mode = get_resize_mode(event.x, event.y)
            self.area_start_width = self.check_area_width
            self.area_start_height = self.check_area_height
            self.area_start_x = area_window.winfo_x()
            self.area_start_y = area_window.winfo_y()
        
        def on_drag(event):
            dx = event.x - self.area_drag_start_x
            dy = event.y - self.area_drag_start_y
            
            if self.area_resize_mode == 'move':
                # Перемещение
                x = self.area_start_x + dx
                y = self.area_start_y + dy
                area_window.geometry(f"+{x}+{y}")
            else:
                # Изменение размеров
                new_width = self.area_start_width
                new_height = self.area_start_height
                new_x = self.area_start_x
                new_y = self.area_start_y
                
                if self.area_resize_mode and 'e' in self.area_resize_mode:
                    new_width = max(50, self.area_start_width + dx)
                if self.area_resize_mode and 'w' in self.area_resize_mode:
                    new_width = max(50, self.area_start_width - dx)
                    new_x = self.area_start_x + dx
                if self.area_resize_mode and 's' in self.area_resize_mode:
                    new_height = max(30, self.area_start_height + dy)
                if self.area_resize_mode and 'n' in self.area_resize_mode:
                    new_height = max(30, self.area_start_height - dy)
                    new_y = self.area_start_y + dy
                
                # Обновляем размеры
                self.check_area_width = new_width
                self.check_area_height = new_height
                
                # Перерисовываем canvas
                canvas.delete('all')
                canvas.config(width=new_width+20, height=new_height+20)
                canvas.create_rectangle(10, 10, new_width+10, new_height+10, 
                                      outline='red', width=3, fill='', dash=(5, 5))
                canvas.create_text(new_width//2+10, new_height//2+10, 
                                  text="Область\nпроверки", font=('Arial', 10, 'bold'), 
                                  fill='red', justify=tk.CENTER)
                
                # Перерисовываем маркеры
                handles = [
                    (10, 10), (new_width+10, 10),
                    (10, new_height+10), (new_width+10, new_height+10)
                ]
                for hx, hy in handles:
                    canvas.create_rectangle(hx-resize_handle_size//2, hy-resize_handle_size//2,
                                          hx+resize_handle_size//2, hy+resize_handle_size//2,
                                          outline='red', fill='red', width=2)
                
                area_window.geometry(f"{new_width+20}x{new_height+20}+{new_x}+{new_y}")
        
        def on_release(event):
            self.check_area_x = area_window.winfo_x() + 10
            self.check_area_y = area_window.winfo_y() + 10
            self.area_resize_mode = None
        
        # Сохраняем функции для привязки/отвязки событий
        self.area_event_handlers = {
            'motion': update_cursor,
            'button1': start_drag,
            'b1motion': on_drag,
            'buttonrelease1': on_release
        }
        
        # По умолчанию НЕ привязываем события - окно неактивно
        # События будут привязаны только при активации через кнопку
        
        # По умолчанию скрываем окно области, чтобы оно не мешало работе с главным окном
        area_window.withdraw()
        
        # Передаём фокус главному окну, чтобы оно могло получать клики
        self.root.focus_force()
        self.root.lift()
        
        # Кнопки управления (в главном окне) - всегда показываем поверх
        if not hasattr(self, 'area_control_frame'):
            self.area_control_frame = tk.Frame(self.root, bg='white', relief=tk.RAISED, bd=2)
            self.area_control_frame.place(x=10, y=10)
            
            save_btn = tk.Button(self.area_control_frame, text="💾 Сохранить", 
                                command=self.save_check_area, bg="#4CAF50", fg="black")
            save_btn.pack(side=tk.LEFT, padx=2)
            
            close_btn = tk.Button(self.area_control_frame, text="✕ Закрыть", 
                                 command=self.close_check_area_editor, bg="#f44336", fg="black")
            close_btn.pack(side=tk.LEFT, padx=2)
            
            # Кнопка для временного скрытия окна области
            hide_btn = tk.Button(self.area_control_frame, text="👁 Скрыть", 
                                command=lambda: self.hide_area_window(area_window), bg="#FF9800", fg="black")
            hide_btn.pack(side=tk.LEFT, padx=2)
            
            # Кнопка для показа окна области
            show_btn = tk.Button(self.area_control_frame, text="👁 Показать", 
                                command=lambda: self.show_area_window(area_window), bg="#2196F3", fg="black")
            show_btn.pack(side=tk.LEFT, padx=2)
            
            # Кнопка для переключения "поверх всех окон"
            self.area_topmost = False
            topmost_btn = tk.Button(self.area_control_frame, text="📌 Поверх", 
                                   bg="#9C27B0", fg="black")
            # Используем замыкание для правильной передачи ссылки
            def toggle_topmost():
                self.toggle_area_topmost(area_window, topmost_btn)
            topmost_btn.config(command=toggle_topmost)
            topmost_btn.pack(side=tk.LEFT, padx=2)
            
            # Кнопка для активации/деактивации взаимодействия с окном области
            self.area_active = False
            active_btn = tk.Button(self.area_control_frame, text="🔓 Активировать", 
                                  bg="#FFC107", fg="black")
            def toggle_active():
                self.toggle_area_active(area_window, active_btn)
            active_btn.config(command=toggle_active)
            active_btn.pack(side=tk.LEFT, padx=2)
        else:
            self.area_control_frame.lift()
    
    def save_check_area(self):
        """Сохраняет координаты области проверки"""
        if self.check_area_window:
            self.check_area_x = self.check_area_window.winfo_x() + 10
            self.check_area_y = self.check_area_window.winfo_y() + 10
            print(f"💾 Область сохранена: x={self.check_area_x}, y={self.check_area_y}, width={self.check_area_width}, height={self.check_area_height}")
            # Сохраняем в файл
            self.save_marker_and_area_settings()
    
    def hide_area_window(self, area_window):
        """Скрывает окно области"""
        if area_window:
            area_window.withdraw()
    
    def show_area_window(self, area_window):
        """Показывает окно области"""
        if area_window:
            area_window.deiconify()
            # При показе окно всё ещё неактивно (события не привязаны)
            # Нужно активировать его отдельно через кнопку "Активировать"
            area_window.lift()
    
    def toggle_area_topmost(self, area_window, button):
        """Переключает режим 'поверх всех окон' для окна области"""
        if not hasattr(self, 'area_topmost'):
            self.area_topmost = False
        
        self.area_topmost = not self.area_topmost
        if area_window:
            area_window.attributes('-topmost', self.area_topmost)
            if self.area_topmost:
                button.config(text="📌 Поверх ✓", bg="#4CAF50")
                area_window.lift()
            else:
                button.config(text="📌 Поверх", bg="#9C27B0")
    
    def toggle_area_active(self, area_window, button):
        """Переключает активность окна области (может ли перехватывать клики)"""
        if not hasattr(self, 'area_active'):
            self.area_active = False
        
        self.area_active = not self.area_active
        if area_window:
            canvas = None
            # Находим canvas в окне
            for widget in area_window.winfo_children():
                if isinstance(widget, tk.Canvas):
                    canvas = widget
                    break
            
            if canvas:
                if self.area_active:
                    # Активируем окно - привязываем события
                    canvas.bind('<Motion>', self.area_event_handlers['motion'])
                    canvas.bind('<Button-1>', self.area_event_handlers['button1'])
                    canvas.bind('<B1-Motion>', self.area_event_handlers['b1motion'])
                    canvas.bind('<ButtonRelease-1>', self.area_event_handlers['buttonrelease1'])
                    area_window.attributes('-topmost', True)
                    button.config(text="🔒 Деактивировать", bg="#F44336")
                    area_window.lift()
                else:
                    # Деактивируем - отвязываем все события
                    canvas.unbind('<Motion>')
                    canvas.unbind('<Button-1>')
                    canvas.unbind('<B1-Motion>')
                    canvas.unbind('<ButtonRelease-1>')
                    area_window.attributes('-topmost', False)
                    button.config(text="🔓 Активировать", bg="#FFC107")
                    # Передаём фокус главному окну
                    self.root.focus_force()
    
    def close_check_area_editor(self):
        """Закрывает редактор области"""
        if self.check_area_window:
            self.save_check_area()
            self.check_area_window.destroy()
            self.check_area_window = None
        if hasattr(self, 'area_control_frame'):
            self.area_control_frame.destroy()
            del self.area_control_frame
    
    def check_no_results_screenshot(self):
        """Проверяет наличие сообщения 'No results' через скриншот области"""
        if not PY_AUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            print("⚠️ pyautogui или PIL недоступны")
            return False
        
        # Проверяем, настроена ли область
        if self.check_area_x is None or self.check_area_y is None:
            print("⚠️ Область не настроена! Нажмите '📐 Настроить область' и разместите рамку на области 'No results'")
            return False
        
        try:
            check_x = self.check_area_x
            check_y = self.check_area_y
            check_width = self.check_area_width
            check_height = self.check_area_height
            
            print(f"🔍 Область проверки: x={check_x}, y={check_y}, width={check_width}, height={check_height}")
            
            # Делаем скриншот области
            if not PY_AUTOGUI_AVAILABLE:
                print("⚠️ pyautogui недоступен")
                return False
            
            import pyautogui  # type: ignore
            screenshot = pyautogui.screenshot(region=(check_x, check_y, check_width, check_height))
            
            # Проверяем наличие красного цвета
            has_red = False
            pixels = screenshot.load()
            if pixels is None:
                print("⚠️ Не удалось загрузить пиксели скриншота")
                return False
            
            red_pixels_count = 0
            total_pixels = check_width * check_height
            
            for x in range(check_width):
                for y in range(check_height):
                    pixel_data = pixels[x, y]  # type: ignore
                    r, g, b = pixel_data
                    # Проверка на красный цвет (R > 200, G < 100, B < 100)
                    if r > 200 and g < 100 and b < 100:
                        red_pixels_count += 1
                        has_red = True
            
            red_percentage = (red_pixels_count / total_pixels) * 100
            
            print(f"🔍 Проверка 'No results':")
            print(f"   Красных пикселей: {red_pixels_count} ({red_percentage:.2f}%)")
            print(f"   Результат: {'✓ Найдено (No results)' if has_red else '✗ Не найдено (есть результаты)'}")
            
            return has_red
            
        except Exception as e:
            print(f"⚠️ Ошибка при проверке скриншота: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_all_elements(self):
        """Получает список всех элементов в окне поиска Cursor и выводит в терминал"""
        try:
            # Шаг 1: Активируем Cursor и открываем окно поиска
            print("🔍 Активация Cursor и открытие окна поиска...")
            script_step1 = '''
            tell application "Cursor"
                activate
            end tell
            delay 0.3
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 3 using command down
                end tell
            end tell
            delay 1.0
            '''
            result_step1 = subprocess.run(['osascript', '-e', script_step1], check=False, capture_output=True, text=True)
            if result_step1.returncode != 0:
                print(f"⚠️ Ошибка при открытии окна поиска: {result_step1.stderr}")
            else:
                print("✓ Команда Cmd+F выполнена")
            time.sleep(0.3)  # Дополнительная пауза в Python
            
            # Шаг 2: Получаем свойства элемента с фокусом
            script_step2 = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    set elementsList to ""
                    
                    -- Ищем элемент с фокусом (это должно быть поле поиска)
                    set elementsList to elementsList & "=== ЭЛЕМЕНТ С ФОКУСОМ (ПОЛЕ ПОИСКА) ===\\n"
                    set focusedElement to missing value
                    try
                        -- Пробуем найти элемент с фокусом через все окна
                        set windowsList to every window
                        repeat with win in windowsList
                            try
                                set focusedElements to every UI element of win whose focused is true
                                if (count of focusedElements) > 0 then
                                    set focusedElement to item 1 of focusedElements
                                    exit repeat
                                end if
                            end try
                        end repeat
                        
                        if focusedElement is not missing value then
                            set feRole to role of focusedElement
                            set feName to name of focusedElement
                            set feValue to ""
                            set feDesc to ""
                            set feClass to ""
                            set feTitle to ""
                            set feHelp to ""
                            
                            try
                                set feValue to value of focusedElement
                            end try
                            try
                                set feDesc to description of focusedElement
                            end try
                            try
                                set feClass to class of focusedElement
                            end try
                            try
                                set feTitle to title of focusedElement
                            end try
                            try
                                set feHelp to help of focusedElement
                            end try
                            
                            set elementsList to elementsList & "ROLE: " & feRole & "\\n"
                            set elementsList to elementsList & "NAME: " & feName & "\\n"
                            set elementsList to elementsList & "VALUE: " & feValue & "\\n"
                            set elementsList to elementsList & "DESCRIPTION: " & feDesc & "\\n"
                            set elementsList to elementsList & "CLASS: " & feClass & "\\n"
                            set elementsList to elementsList & "TITLE: " & feTitle & "\\n"
                            set elementsList to elementsList & "HELP: " & feHelp & "\\n"
                            
                            -- Пытаемся получить родительский элемент
                            try
                                set parentElem to parent of focusedElement
                                set parentRole to role of parentElem
                                set parentName to name of parentElem
                                set elementsList to elementsList & "\\nPARENT: ROLE: " & parentRole & " | NAME: " & parentName & "\\n"
                            end try
                            
                            -- Пытаемся получить соседние элементы (для навигации)
                            try
                                set elementsList to elementsList & "\\n=== СОСЕДНИЕ ЭЛЕМЕНТЫ ===\\n"
                                set parentElem to parent of focusedElement
                                set siblings to every UI element of parentElem
                                set siblingCount to count of siblings
                                set elementsList to elementsList & "Всего элементов в родителе: " & siblingCount & "\\n"
                                set indexNum to 1
                                repeat with sibling in siblings
                                    try
                                        set sibRole to role of sibling
                                        set sibName to name of sibling
                                        set sibFocused to focused of sibling
                                        set elementsList to elementsList & "  [" & indexNum & "] ROLE: " & sibRole & " | NAME: " & sibName & " | FOCUSED: " & sibFocused & "\\n"
                                        set indexNum to indexNum + 1
                                    end try
                                end repeat
                            end try
                        else
                            set elementsList to elementsList & "Элемент с фокусом не найден!\\n"
                        end if
                    on error errMsg
                        set elementsList to elementsList & "ОШИБКА при поиске элемента с фокусом: " & errMsg & "\\n"
                    end try
                    
                    set elementsList to elementsList & "\\n=== ПОИСК ПО ОКНАМ (для справки) ===\\n"
                    try
                        set windowsList to every window
                        repeat with win in windowsList
                            try
                                set winTitle to title of win
                                set elementsList to elementsList & "=== WINDOW: " & winTitle & " ===\\n"
                                
                                -- Получаем все элементы с глубоким поиском (до 3 уровней вложенности)
                                set uiElements to every UI element of win
                                repeat with elem in uiElements
                                    -- Уровень 0
                                    try
                                        set elemRole to role of elem
                                        set elemName to name of elem
                                        set elemFocused to ""
                                        set elemValue to ""
                                        set elemDescription to ""
                                        
                                        try
                                            set elemFocused to focused of elem
                                        end try
                                        try
                                            set elemValue to value of elem
                                        end try
                                        try
                                            set elemDescription to description of elem
                                        end try
                                        
                                        set elementsList to elementsList & "ROLE: " & elemRole & " | NAME: " & elemName & " | FOCUSED: " & elemFocused & " | VALUE: " & elemValue & " | DESC: " & elemDescription & "\\n"
                                        
                                        -- Уровень 1
                                        try
                                            set subElements1 to every UI element of elem
                                            repeat with subElem1 in subElements1
                                                try
                                                    set subRole1 to role of subElem1
                                                    set subName1 to name of subElem1
                                                    set subFocused1 to focused of subElem1
                                                    set subValue1 to ""
                                                    try
                                                        set subValue1 to value of subElem1
                                                    end try
                                                    set elementsList to elementsList & "  └─ L1: ROLE: " & subRole1 & " | NAME: " & subName1 & " | FOCUSED: " & subFocused1 & " | VALUE: " & subValue1 & "\\n"
                                                    
                                                    -- Уровень 2
                                                    try
                                                        set subElements2 to every UI element of subElem1
                                                        repeat with subElem2 in subElements2
                                                            try
                                                                set subRole2 to role of subElem2
                                                                set subName2 to name of subElem2
                                                                set subFocused2 to focused of subElem2
                                                                set subValue2 to ""
                                                                try
                                                                    set subValue2 to value of subElem2
                                                                end try
                                                                set elementsList to elementsList & "    └─ L2: ROLE: " & subRole2 & " | NAME: " & subName2 & " | FOCUSED: " & subFocused2 & " | VALUE: " & subValue2 & "\\n"
                                                                
                                                                -- Уровень 3 (для текстовых полей поиска)
                                                                try
                                                                    set subElements3 to every UI element of subElem2
                                                                    repeat with subElem3 in subElements3
                                                                        try
                                                                            set subRole3 to role of subElem3
                                                                            set subName3 to name of subElem3
                                                                            set subFocused3 to focused of subElem3
                                                                            set subValue3 to ""
                                                                            try
                                                                                set subValue3 to value of subElem3
                                                                            end try
                                                                            set elementsList to elementsList & "      └─ L3: ROLE: " & subRole3 & " | NAME: " & subName3 & " | FOCUSED: " & subFocused3 & " | VALUE: " & subValue3 & "\\n"
                                                                        end try
                                                                    end repeat
                                                                end try
                                                            end try
                                                        end repeat
                                                    end try
                                                end try
                                            end repeat
                                        end try
                                    end try
                                end repeat
                            end try
                        end repeat
                        return elementsList
                    on error errMsg
                        return "ERROR: " & errMsg
                    end try
                end tell
            end tell
            '''
            print("🔍 Поиск элементов...")
            result = subprocess.run(['osascript', '-e', script_step2], check=False, capture_output=True, text=True)
            if result.returncode == 0:
                print("\n" + "="*80)
                print("СПИСОК ВСЕХ ЭЛЕМЕНТОВ В CURSOR (после открытия окна поиска):")
                print("="*80)
                if result.stdout:
                    print(result.stdout)
                else:
                    print("Нет вывода от AppleScript")
                if result.stderr:
                    print("ОШИБКИ:")
                    print(result.stderr)
                print("="*80 + "\n")
                
                # Анализ результатов
                if "TEXT FIELD" not in result.stdout and "TEXT AREA" not in result.stdout:
                    print("⚠️ ВНИМАНИЕ: Текстовые поля не найдены!")
                    print("   Возможные причины:")
                    print("   1. Окно поиска не открылось")
                    print("   2. Элементы недоступны через AppleScript (WebView/Electron)")
                    print("   3. Требуется больше времени для загрузки")
                    print("\n💡 Попробуйте:")
                    print("   - Вручную открыть окно поиска (Cmd+F) перед нажатием кнопки")
                    print("   - Убедиться, что окно поиска видно на экране")
                    print()
            else:
                print(f"❌ Ошибка выполнения AppleScript. Код возврата: {result.returncode}")
                if result.stderr:
                    print(f"Ошибка: {result.stderr}")
        except Exception as e:
            print(f"Ошибка при получении элементов: {e}")
            import traceback
            traceback.print_exc()

    def apply_replace(self):
        old = self.old_entry.get("1.0", tk.END).rstrip('\n')
        new = self.new_entry.get("1.0", tk.END).rstrip('\n')
        
        if not old:
            return
        
        if not PY_AUTOGUI_AVAILABLE:
            return
        
        try:
            # Активируем окно Cursor
            self.activate_cursor_window()
            time.sleep(0.05)
            
            # Используем координаты маркера для клика
            if self.marker_x is None or self.marker_y is None:
                # Если маркер не был перемещён, используем координаты относительно окна
                self.root.update_idletasks()
                window_x = self.root.winfo_x()
                window_y = self.root.winfo_y()
                click_x = window_x - 100
                click_y = window_y - 50
                self.marker_x = click_x
                self.marker_y = click_y
            
            click_x = self.marker_x
            click_y = self.marker_y
            
            success = self.click_with_applescript(click_x, click_y)
            if not success and PY_AUTOGUI_AVAILABLE:
                import pyautogui  # type: ignore
                pyautogui.click(click_x, click_y, clicks=2, interval=0.1)
            
            time.sleep(0.05)
            
            # Дополнительный клик в редактор для гарантии фокуса
            success = self.click_with_applescript(click_x, click_y)
            if not success and PY_AUTOGUI_AVAILABLE:
                import pyautogui  # type: ignore
                pyautogui.click(click_x, click_y)
            
            # Открываем поиск (Cmd+F)
            # Используем key code 3 для клавиши F вместо keystroke
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 3 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            
            # Вставляем старый текст в поле Find (Cmd+A, затем Cmd+V)
            pyperclip.copy(old)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 0 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 9 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
            # Shift+Tab для перехода на кнопку Toggle Replace
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 48 using shift down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
            # Space для активации кнопки (открытие поля замены)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 49
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
            # 2 раза Tab для перехода в поле Replace
            for i in range(2):
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 48
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
            time.sleep(0.05)
            
            # Вставляем новый текст в поле Replace (Cmd+A, затем Cmd+V)
            pyperclip.copy(new)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 0 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 9 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.3)  # Пауза для появления результатов поиска
            
            # Проверяем наличие "No results" через скриншот
            has_no_results = self.check_no_results_screenshot()
            
            # Завершаем выполнение
            # return

            # 9 раз Tab для перехода на кнопку замены
            for i in range(9):
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 48
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
            time.sleep(0.05)
            
            # Space для выполнения замены
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 49
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.1)
            # Второе нажатие Space для выполнения замены (первое активирует найденное, второе выполняет замену)
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.1)
            
            # Алгоритм проверки позиции через буфер обмена
            # Количество шагов назад зависит от наличия результатов поиска
            # Если "No results" - делаем 8 шагов, иначе 6 шагов
            steps_back = 8 if has_no_results else 6
            
            print(f"📊 Используем {steps_back} шагов назад (No results: {has_no_results})")
            
            # Очищаем буфер перед проверкой
            pyperclip.copy("")
            time.sleep(0.05)
            
            # Делаем шаги назад (Shift+Tab)
            for i in range(steps_back):
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 48 using shift down
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
            time.sleep(0.1)
            
            # Выделяем всё содержимое поля (Cmd+A) и копируем в буфер (Cmd+C)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 0 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 8 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.1)
            
            # Сравниваем содержимое буфера с new_text
            clipboard_content = pyperclip.paste()
            if clipboard_content == new:
                # Мы в поле Replace - очищаем его
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 0 using command down
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 51
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
            else:
                # Делаем ещё 2 шага назад (итого 8)
                for i in range(2):
                    script = '''
                    tell application "System Events"
                        tell process "Cursor"
                            set frontmost to true
                            key code 48 using shift down
                        end tell
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                    time.sleep(0.05)
                time.sleep(0.1)
                
                # Очищаем буфер, выделяем всё (Cmd+A) и копируем снова (Cmd+C)
                pyperclip.copy("")
                time.sleep(0.05)
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 0 using command down
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.05)
                script = '''
                tell application "System Events"
                    tell process "Cursor"
                        set frontmost to true
                        key code 8 using command down
                    end tell
                end tell
                '''
                subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                time.sleep(0.1)
                
                # Сравниваем снова
                clipboard_content = pyperclip.paste()
                if clipboard_content == new:
                    # Мы в поле Replace - очищаем его
                    script = '''
                    tell application "System Events"
                        tell process "Cursor"
                            set frontmost to true
                            key code 0 using command down
                        end tell
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                    time.sleep(0.05)
                    script = '''
                    tell application "System Events"
                        tell process "Cursor"
                            set frontmost to true
                            key code 51
                        end tell
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
                    time.sleep(0.05)
                else:
                    print(f"⚠️ Ошибка: не удалось найти поле Replace. Буфер содержит: '{clipboard_content}', ожидалось: '{new}'")
                    return
            
            # Делаем один шаг назад (Shift+Tab) - попадаем в поле Find
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 48 using shift down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
            # Выделяем значение поля Find (Cmd+A) и очищаем его (Delete)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 0 using command down
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 51
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
            # Escape для закрытия окна поиска
            script = '''
            tell application "System Events"
                tell process "Cursor"
                    set frontmost to true
                    key code 53
                end tell
            end tell
            '''          
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True, text=True)
            time.sleep(0.05)
            
        except Exception:
            pass
    
    def create_draggable_marker(self):
        """Создаёт перемещаемый маркер для указания точки клика"""
        # Начальная позиция - из сохранённых настроек или центр экрана
        if self.marker_x is not None and self.marker_y is not None:
            initial_x = self.marker_x
            initial_y = self.marker_y
        else:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            initial_x = screen_width // 2
            initial_y = screen_height // 2
        
        # Создаём маркер как полностью независимое окно (без родителя)
        marker = tk.Toplevel()
        marker.overrideredirect(True)
        marker.attributes('-topmost', True)
        marker.attributes('-alpha', 0.9)
        # КРИТИЧНО: Маркер НЕ должен перехватывать фокус
        marker.takefocus = False
        marker.focus_set = lambda: None  # Отключаем установку фокуса
        
        # Круглый маркер
        canvas = tk.Canvas(marker, width=50, height=50, highlightthickness=0, bg='red', cursor='hand2', takefocus=0)
        canvas.pack()
        # Рисуем круг
        canvas.create_oval(5, 5, 45, 45, fill='red', outline='darkred', width=3)
        canvas.create_text(25, 25, text='+', font=('Arial', 20, 'bold'), fill='white')
        
        marker.geometry(f"50x50+{initial_x-25}+{initial_y-25}")
        self.marker_window = marker
        
        # Переменные для перетаскивания
        self.marker_drag_start_x = 0
        self.marker_drag_start_y = 0
        
        def start_drag(event):
            self.marker_drag_start_x = event.x
            self.marker_drag_start_y = event.y
            # КРИТИЧНО: Сразу возвращаем фокус главному окну
            self.root.after_idle(lambda: self.root.focus_force())
        
        def on_drag(event):
            x = marker.winfo_x() + event.x - self.marker_drag_start_x
            y = marker.winfo_y() + event.y - self.marker_drag_start_y
            marker.geometry(f"+{x}+{y}")
            # Обновляем координаты для клика
            self.marker_x = x + 25  # Центр маркера
            self.marker_y = y + 25
            # КРИТИЧНО: Постоянно возвращаем фокус главному окну при перетаскивании
            self.root.after_idle(lambda: self.root.focus_force())
        
        def on_release(event):
            # Сохраняем финальные координаты
            self.marker_x = marker.winfo_x() + 25
            self.marker_y = marker.winfo_y() + 25
            # КРИТИЧНО: Возвращаем фокус главному окну после отпускания
            self.root.after_idle(lambda: self.root.focus_force())
            # Автоматически сохраняем при изменении
            self.save_marker_and_area_settings()
        
        # КРИТИЧНО: Переопределяем обработчики, чтобы они не перехватывали фокус
        def safe_start_drag(event):
            start_drag(event)
            self.root.after_idle(lambda: self.root.focus_force())
        def safe_on_drag(event):
            on_drag(event)
            self.root.after_idle(lambda: self.root.focus_force())
        def safe_on_release(event):
            on_release(event)
            self.root.after_idle(lambda: self.root.focus_force())
        
        canvas.bind('<Button-1>', safe_start_drag)
        canvas.bind('<B1-Motion>', safe_on_drag)
        canvas.bind('<ButtonRelease-1>', safe_on_release)
        
        # Инициализируем координаты
        self.marker_x = initial_x
        self.marker_y = initial_y
        
        # Функция для принудительного поддержания маркера поверх всех окон
        def keep_marker_on_top():
            try:
                marker.attributes('-topmost', True)
                marker.lift()
                # КРИТИЧНО: Постоянно возвращаем фокус главному окну
                try:
                    current_focus = marker.focus_get()
                    if current_focus == marker or current_focus is None:
                        self.root.focus_force()
                except:
                    self.root.focus_force()
            except Exception:
                pass
            # Повторяем каждые 50мс для гарантии
            marker.after(50, keep_marker_on_top)
        
        # Функция для постоянного возврата фокуса главному окну
        def keep_focus_on_root():
            try:
                # Проверяем, не перехватил ли маркер фокус
                current_focus = self.root.focus_get()
                if current_focus != self.root and current_focus is not None:
                    # Если фокус не на главном окне, возвращаем его
                    self.root.focus_force()
            except:
                pass
            # Повторяем каждые 100мс
            self.root.after(100, keep_focus_on_root)
        
        # Запускаем периодическое обновление
        marker.after(50, keep_marker_on_top)
        self.root.after(100, keep_focus_on_root)
        
        # Убеждаемся, что главное окно имеет фокус
        self.root.focus_force()
    
    def show_click_marker(self, x, y):
        """Показывает визуальный маркер в точке клика (устаревший метод, оставлен для совместимости)"""
        # Используем существующий перемещаемый маркер
        if self.marker_window:
            self.marker_window.geometry(f"50x50+{x-25}+{y-25}")
            self.marker_x = x
            self.marker_y = y
    
    def clear_fields(self):
        self.old_entry.delete("1.0", tk.END)
        self.new_entry.delete("1.0", tk.END)
        self.old_text.set("")
        self.new_text.set("")
    
    def load_window_settings(self):
        """Загружает сохранённые настройки окна из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Проверяем валидность данных
                    if all(key in settings for key in ['width', 'height', 'x', 'y']):
                        # Обновляем окно для получения корректных размеров экрана
                        self.root.update_idletasks()
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        # Проверяем, что окно не выходит за пределы экрана
                        if (0 <= settings['x'] < screen_width and 
                            0 <= settings['y'] < screen_height and
                            settings['width'] > 200 and settings['height'] > 200):
                            return settings
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке настроек: {e}")
        return None
    
    def save_window_settings(self):
        """Сохраняет текущие размер и позицию окна в файл"""
        try:
            # Получаем текущие размеры и позицию
            geometry = self.root.geometry()
            # Формат: "widthxheight+x+y"
            parts = geometry.split('+')
            size_parts = parts[0].split('x')
            width = int(size_parts[0])
            height = int(size_parts[1])
            x = int(parts[1])
            y = int(parts[2])
            
            settings = {
                'width': width,
                'height': height,
                'x': x,
                'y': y
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении настроек: {e}")
    
    def on_window_configure(self, event):
        """Обработчик изменения размера или позиции окна"""
        # Сохраняем только если это главное окно (не дочерние)
        if event.widget == self.root:
            # Используем after для отложенного сохранения (чтобы не сохранять при каждом пикселе)
            if not hasattr(self, '_save_timer'):
                self._save_timer = None
            
            # Отменяем предыдущий таймер
            if self._save_timer:
                self.root.after_cancel(self._save_timer)
            
            # Устанавливаем новый таймер (сохраним через 500мс после последнего изменения)
            self._save_timer = self.root.after(500, self.save_window_settings)
    
    def on_root_focus_in(self, event):
        """Обработчик получения фокуса главным окном - убеждаемся, что фокус остаётся на главном окне"""
        # Убеждаемся, что дочерние окна не перехватывают фокус
        if self.marker_window:
            try:
                if self.marker_window.focus_get() == self.marker_window:
                    self.root.focus_force()
            except:
                pass
        
        if self.check_area_window:
            try:
                if self.check_area_window.focus_get() == self.check_area_window:
                    self.root.focus_force()
            except:
                pass
    
    def on_closing(self):
        """Обработчик закрытия окна - сохраняет настройки перед выходом"""
        self.save_window_settings()
        self.save_marker_and_area_settings()
        self.root.destroy()
    
    def load_marker_and_area_settings(self):
        """Загружает сохранённые настройки маркера и области проверки"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Загружаем настройки маркера
                    if 'marker_x' in settings and 'marker_y' in settings:
                        self.marker_x = settings['marker_x']
                        self.marker_y = settings['marker_y']
                    # Загружаем настройки области проверки
                    if 'check_area_x' in settings and 'check_area_y' in settings:
                        self.check_area_x = settings['check_area_x']
                        self.check_area_y = settings['check_area_y']
                    if 'check_area_width' in settings:
                        self.check_area_width = settings['check_area_width']
                    if 'check_area_height' in settings:
                        self.check_area_height = settings['check_area_height']
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке настроек маркера и области: {e}")
    
    def save_marker_and_area_settings(self):
        """Сохраняет настройки маркера и области проверки в файл"""
        try:
            # Загружаем существующие настройки, если файл есть
            settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # Обновляем настройки маркера
            if self.marker_x is not None and self.marker_y is not None:
                settings['marker_x'] = self.marker_x
                settings['marker_y'] = self.marker_y
            
            # Обновляем настройки области проверки
            if self.check_area_x is not None and self.check_area_y is not None:
                settings['check_area_x'] = self.check_area_x
                settings['check_area_y'] = self.check_area_y
                settings['check_area_width'] = self.check_area_width
                settings['check_area_height'] = self.check_area_height
            
            # Сохраняем в файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении настроек маркера и области: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = FindReplaceHelper()
    app.run()