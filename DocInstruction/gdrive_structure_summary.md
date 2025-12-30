# Структура Google Drive для компонентов

## Базовая папка
**ID:** `1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW`  
**URL:** `https://drive.google.com/drive/folders/1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW`

## Структура папок и файлов

### 📁 Wine
- **ID папки:** `1wpI5WgbU6zERBWlKmW-8HfNG0h23funw`
- **Файлы:**
  - `wine_packages.tar.gz` (110.5 МБ по скриншоту)
  - **SHA256:** *требуется вычисление*

### 📁 Winetricks
- **ID папки:** `1F1cqcg2t4rbOtuiRLLWQSWVEBdl3G00o`
- **Файлы:**
  - `winetricks_packages.tar.gz` (416.30 МБ)
  - **SHA256:** `b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e`

### 📁 Count
- **ID папки:** `1e0-DhlgiFvtmx2FX0E00sPWTXH_rUD59`
- **Файлы:**
  - `CountPack.tar.gz` (размер неизвестен)
  - **SHA256:** *требуется вычисление*

### 📁 Astra
- **ID папки:** `1AsTk3DiGfEo3-EOlJo79j6iPJy6Ax5gu`
- **Файлы:**
  - `AstraPack.tar.gz` (размер неизвестен)
  - **SHA256:** *требуется вычисление*

## Конфигурация remote_source для компонентов

### 1. cont_designer
```python
'remote_source': {
    'type': 'gdrive',
    'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
    'folder_path': 'Count',  # Относительно базовой папки
    'file_name': 'CountPack.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Cont/CountPack.tar.gz',
    'sha256': None  # Требуется после загрузки
}
```

### 2. astra_wine_9 и astra_wine_astraregul
```python
'remote_source': {
    'type': 'gdrive',
    'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
    'folder_path': 'Wine',
    'file_name': 'wine_packages.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Wine/wine_packages.tar.gz',
    'sha256': None  # Требуется после загрузки
}
```

### 3. astra_wineprefix
```python
'remote_source': {
    'type': 'gdrive',
    'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
    'folder_path': 'Winetricks',
    'file_name': 'winetricks_packages.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Winetricks/winetricks_packages.tar.gz',
    'sha256': 'b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e'
}
```

### 4. astra_ide
```python
'remote_source': {
    'type': 'gdrive',
    'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
    'folder_path': 'Astra',
    'file_name': 'AstraPack.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Astra/AstraPack.tar.gz',
    'sha256': None  # Требуется после загрузки
}
```

## Формат пути в remote_source

Используется структура:
- **base_folder_id** - ID корневой папки
- **folder_path** - имя подпапки (Wine, Count, Winetricks, Astra)
- **file_name** - имя файла в подпапке

Это позволяет использовать относительные пути от базовой папки, что упрощает управление структурой.

