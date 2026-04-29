# yhilbot

Discord-бот для медиа-редактирования: конвертация в GIF/WebP, мем-капшены поверх картинок, и QUAD видеоредактор с таймлайном на ffmpeg.

## Команды

| Команда | Описание |
|---|---|
| `/gif [media]` | Конвертирует видео → анимированный WebP, изображение → GIF. Авто-подбор разрешения и FPS под лимит Discord (~25 МБ). |
| `/caption <text> [media]` | Накладывает мем-заголовок шрифтом Impact поверх картинки. |
| `/edit [media] [join_code]` | Видеоредактор с таймлайном: split, текстовые наложения, скорость, разрешение, FPS, undo/redo, фоновый рендер. |
| `/stats` | Статистика бота, ресурсов и очереди (только для `OWNER_ID`). |
| `/help` | Список команд. |

`media` можно не указывать — бот возьмёт первое медиа из последних 15 сообщений канала.

## Установка

```bash
# Клонирование
git clone https://github.com/c8rnell8/yhilbot.git
cd yhilbot

# Зависимости (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Конфиг
cp yhil.env.example yhil.env
# отредактируй yhil.env, проставь DISCORD_TOKEN и OWNER_ID

# Запуск
python bot.py
```

## Системные требования

- Python ≥ 3.10
- ffmpeg + ffprobe в `$PATH` (поддержка libwebp, libgif, drawtext)
- Шрифт Impact (или fallback Liberation/DejaVu) — для `/caption`
- (Опционально) `h264_nvenc` для ускорения рендера через GPU
- (Опционально) `psutil` для расширенной статистики

## Структура проекта

```
bot.py                           # точка входа
yhilbot/
├── config.py                    # env-конфиг и пути
├── logging_setup.py             # логгер
├── stats.py                     # счётчики (атомарные)
├── client.py                    # Discord-клиент и command tree
├── ffmpeg_helpers.py            # обёртки над ffmpeg/ffprobe + escape
├── media_utils.py               # скачивание и поиск медиа в канале
├── caption_render.py            # PIL-рендер /caption
├── queue_mgr.py                 # глобальная очередь /gif
├── cache.py                     # render_cache/gif_cache helpers
├── lifecycle.py                 # on_ready, graceful exit
├── editor/
│   ├── models.py                # Clip/Overlay/Timeline/EditorSession
│   ├── db.py                    # sqlite + thread-local conn
│   ├── history.py               # undo/redo
│   ├── preview.py               # генерация превью-кадра
│   ├── render.py                # фоновый рендер с прогрессом
│   ├── modals.py                # TimeModal, TextOverlayModal
│   ├── view.py                  # EditorView (UI кнопки и селекты)
│   └── cleanup.py               # фоновая очистка истёкших сессий и кэша
└── commands/
    ├── gif_cmd.py
    ├── caption_cmd.py
    ├── edit_cmd.py
    ├── stats_cmd.py
    └── help_cmd.py
```

## Лимиты по умолчанию

- Вход: до 100 МБ (`MAX_INPUT_MB`)
- Видео: до 5 минут
- Выход: ≤ 24.5 МБ (Discord без буста)
- История правок: 25 шагов
- Таймаут редактора: 15 минут неактивности
- TTL кэша: 2 часа

## Разработка

```bash
pip install ruff
ruff check yhilbot bot.py
```

## Лицензия

См. файл `LICENSE` (если есть).
