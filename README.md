# SVG Template API Server

Полноценный API сервер для генерации SVG карусели с поддержкой всех необходимых endpoints.

## Endpoints

### Health Check
- `GET /health` - Проверка состояния API

### Templates
- `GET /api/templates/all-previews` - Получить все шаблоны с превью
- `GET /api/templates/{id}/preview` - Получить превью конкретного шаблона

### Carousel Generation
- `POST /api/carousel` - Создать новую карусель
- `POST /api/carousel/{id}/generate` - Запустить генерацию карусели
- `GET /api/carousel/{id}/slides` - Получить статус и результаты генерации
- `GET /api/carousel/{id}/slide/{number}` - Получить конкретный слайд

## Деплой на Render.com

1. Создайте новый Web Service на Render.com
2. Подключите этот репозиторий
3. Render автоматически обнаружит Procfile и развернет приложение
4. Обновите URL в вашем React приложении

## Локальное тестирование

```bash
pip install -r requirements.txt
python app.py
```

API будет доступен на http://localhost:5000
