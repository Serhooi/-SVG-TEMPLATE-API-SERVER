#!/usr/bin/env python3
"""
ИСПРАВЛЕННЫЙ API сервер с правильными CORS настройками для agentflow-marketing-hub.vercel.app
"""

import os
import sqlite3
import json
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import tempfile
import subprocess
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import io

# Создаем Flask приложение
app = Flask(__name__)

# ИСПРАВЛЕННЫЕ CORS НАСТРОЙКИ для вашего домена
CORS(app, 
     origins=[
         'https://agentflow-marketing-hub.vercel.app',
         'http://localhost:3000',
         'http://localhost:5173',
         'https://vahgmyuowsilbxqdjjii.supabase.co'
     ],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Accept', 'Authorization', 'apikey'],
     supports_credentials=True
)

# Конфигурация
DATABASE_PATH = 'templates.db'
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'

# Создаем необходимые папки
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def init_database():
    """Инициализация базы данных с созданием всех необходимых таблиц"""
    print("🔧 Инициализация базы данных...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Создаем таблицу templates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            svg_content TEXT NOT NULL,
            preview_url TEXT,
            template_type TEXT DEFAULT 'flyer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем таблицу carousels
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carousels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT
        )
    ''')
    
    # Создаем таблицу carousel_slides
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carousel_slides (
            id TEXT PRIMARY KEY,
            carousel_id TEXT NOT NULL,
            template_id TEXT NOT NULL,
            replacements TEXT NOT NULL,
            slide_order INTEGER NOT NULL,
            output_url TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (carousel_id) REFERENCES carousels (id),
            FOREIGN KEY (template_id) REFERENCES templates (id)
        )
    ''')
    
    # Проверяем есть ли уже шаблоны
    cursor.execute('SELECT COUNT(*) FROM templates')
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("📦 Добавляем тестовые шаблоны...")
        
        test_templates = [
            {
                'id': 'open-house-main',
                'name': 'Open House - Main Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#f0f8ff"/>
                    <text x="200" y="100" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">OPEN HOUSE</text>
                    <text x="200" y="200" text-anchor="middle" font-size="18" fill="#666">{dyno.propertyaddress}</text>
                    <text x="200" y="250" text-anchor="middle" font-size="16" fill="#666">Agent: {dyno.name}</text>
                    <text x="200" y="300" text-anchor="middle" font-size="16" fill="#666">Phone: {dyno.phone}</text>
                    <text x="200" y="350" text-anchor="middle" font-size="16" fill="#666">Date: {dyno.date}</text>
                    <text x="200" y="400" text-anchor="middle" font-size="16" fill="#666">Time: {dyno.time}</text>
                </svg>'''
            },
            {
                'id': 'open-house-photo',
                'name': 'Open House - Photo Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#fff"/>
                    <rect x="50" y="50" width="300" height="200" fill="#ddd" stroke="#999"/>
                    <text x="200" y="160" text-anchor="middle" font-size="14" fill="#666">Property Photo</text>
                    <text x="200" y="300" text-anchor="middle" font-size="20" font-weight="bold" fill="#333">OPEN HOUSE</text>
                    <text x="200" y="350" text-anchor="middle" font-size="16" fill="#666">{dyno.propertyaddress}</text>
                    <text x="200" y="400" text-anchor="middle" font-size="14" fill="#666">Agent: {dyno.name}</text>
                    <text x="200" y="430" text-anchor="middle" font-size="14" fill="#666">Phone: {dyno.phone}</text>
                    <text x="200" y="460" text-anchor="middle" font-size="14" fill="#666">{dyno.date} at {dyno.time}</text>
                </svg>'''
            },
            {
                'id': 'sold-main',
                'name': 'Sold - Main Template',
                'category': 'sold',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#ffe4e1"/>
                    <text x="200" y="100" text-anchor="middle" font-size="28" font-weight="bold" fill="#d2691e">SOLD!</text>
                    <text x="200" y="200" text-anchor="middle" font-size="18" fill="#666">{dyno.propertyaddress}</text>
                    <text x="200" y="300" text-anchor="middle" font-size="16" fill="#666">Sold by: {dyno.name}</text>
                    <text x="200" y="350" text-anchor="middle" font-size="16" fill="#666">Phone: {dyno.phone}</text>
                    <text x="200" y="450" text-anchor="middle" font-size="14" fill="#666">Thank you for choosing us!</text>
                </svg>'''
            },
            {
                'id': 'sold-photo',
                'name': 'Sold - Photo Template',
                'category': 'sold',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#fff"/>
                    <rect x="50" y="50" width="300" height="200" fill="#ddd" stroke="#999"/>
                    <text x="200" y="160" text-anchor="middle" font-size="14" fill="#666">Property Photo</text>
                    <text x="200" y="300" text-anchor="middle" font-size="24" font-weight="bold" fill="#d2691e">SOLD!</text>
                    <text x="200" y="350" text-anchor="middle" font-size="16" fill="#666">{dyno.propertyaddress}</text>
                    <text x="200" y="400" text-anchor="middle" font-size="14" fill="#666">Sold by: {dyno.name}</text>
                    <text x="200" y="430" text-anchor="middle" font-size="14" fill="#666">Phone: {dyno.phone}</text>
                </svg>'''
            }
        ]
        
        for template in test_templates:
            cursor.execute('''
                INSERT INTO templates (id, name, category, svg_content, template_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (template['id'], template['name'], template['category'], 
                  template['svg_content'], template['template_type']))
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована успешно!")

def generate_png_from_svg(svg_content, output_path, width=400, height=600):
    """Генерирует PNG изображение из SVG контента"""
    try:
        print(f"🎨 Генерирую PNG: {output_path}")
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Конвертируем SVG в PNG используя cairosvg
        cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            write_to=output_path,
            output_width=width,
            output_height=height
        )
        
        print(f"✅ PNG сгенерирован: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации PNG: {e}")
        
        # Fallback: создаем простое изображение с текстом
        try:
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Пытаемся загрузить шрифт
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            draw.text((width//2, height//2), "Generated Image", fill='black', font=font, anchor='mm')
            img.save(output_path, 'PNG')
            
            print(f"✅ Fallback PNG создан: {output_path}")
            return True
            
        except Exception as fallback_error:
            print(f"❌ Fallback тоже не сработал: {fallback_error}")
            return False

def replace_svg_placeholders(svg_content, replacements):
    """Заменяет плейсхолдеры в SVG контенте"""
    try:
        replacements_dict = json.loads(replacements) if isinstance(replacements, str) else replacements
        
        for key, value in replacements_dict.items():
            placeholder = f"{{{key}}}"
            svg_content = svg_content.replace(placeholder, str(value))
            
        return svg_content
        
    except Exception as e:
        print(f"❌ Ошибка замены плейсхолдеров: {e}")
        return svg_content

# Инициализируем базу данных при запуске
init_database()

# ДОБАВЛЯЕМ ОБРАБОТКУ OPTIONS REQUESTS
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add("Access-Control-Allow-Origin", "https://agentflow-marketing-hub.vercel.app")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Accept,Authorization,apikey")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

@app.after_request
def after_request(response):
    """Добавляем CORS заголовки ко всем ответам"""
    origin = request.headers.get('Origin')
    allowed_origins = [
        'https://agentflow-marketing-hub.vercel.app',
        'http://localhost:3000',
        'http://localhost:5173',
        'https://vahgmyuowsilbxqdjjii.supabase.co'
    ]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept,Authorization,apikey')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния API"""
    return jsonify({
        'status': 'healthy',
        'message': 'SVG Template API is running',
        'timestamp': datetime.now().isoformat(),
        'cors_enabled': True,
        'allowed_origins': [
            'https://agentflow-marketing-hub.vercel.app',
            'http://localhost:3000',
            'http://localhost:5173'
        ]
    })

@app.route('/api/templates/all-previews', methods=['GET'])
def get_all_templates():
    """Получить все шаблоны с превью"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, category, template_type, created_at
            FROM templates
            ORDER BY created_at DESC
        ''')
        
        templates = []
        for row in cursor.fetchall():
            template_id, name, category, template_type, created_at = row
            templates.append({
                'id': template_id,
                'name': name,
                'category': category,
                'template_type': template_type,
                'preview_url': f'/api/templates/{template_id}/preview',
                'created_at': created_at
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(templates),
            'templates': templates
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/carousel', methods=['POST'])
def create_carousel():
    """Создать новую карусель"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'slides' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, slides'
            }), 400
        
        carousel_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Создаем карусель
        cursor.execute('''
            INSERT INTO carousels (id, name, status)
            VALUES (?, ?, 'created')
        ''', (carousel_id, data['name']))
        
        # Создаем слайды
        for i, slide in enumerate(data['slides']):
            slide_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO carousel_slides (id, carousel_id, template_id, replacements, slide_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (slide_id, carousel_id, slide['templateId'], 
                  json.dumps(slide['replacements']), i + 1))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'carouselId': carousel_id,
            'status': 'created',
            'message': 'Carousel created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ДОБАВЛЯЕМ НЕДОСТАЮЩИЙ ENDPOINT
@app.route('/api/carousel/create-and-generate', methods=['POST'])
def create_and_generate_carousel():
    """Создать карусель и сразу запустить генерацию"""
    try:
        # Сначала создаем карусель
        create_response = create_carousel()
        
        if create_response.status_code != 200:
            return create_response
            
        create_data = create_response.get_json()
        carousel_id = create_data['carouselId']
        
        # Затем запускаем генерацию
        return generate_carousel(carousel_id)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/carousel/<carousel_id>/generate', methods=['POST'])
def generate_carousel(carousel_id):
    """Запустить генерацию карусели"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование карусели
        cursor.execute('SELECT id, name FROM carousels WHERE id = ?', (carousel_id,))
        carousel = cursor.fetchone()
        
        if not carousel:
            return jsonify({
                'success': False,
                'error': 'Carousel not found'
            }), 404
        
        # Обновляем статус на "generating"
        cursor.execute('''
            UPDATE carousels 
            SET status = 'generating' 
            WHERE id = ?
        ''', (carousel_id,))
        
        # Получаем слайды для генерации
        cursor.execute('''
            SELECT cs.id, cs.template_id, cs.replacements, cs.slide_order, t.svg_content
            FROM carousel_slides cs
            JOIN templates t ON cs.template_id = t.id
            WHERE cs.carousel_id = ?
            ORDER BY cs.slide_order
        ''', (carousel_id,))
        
        slides = cursor.fetchall()
        
        # РЕАЛЬНАЯ ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ
        for slide_id, template_id, replacements_json, slide_order, svg_content in slides:
            try:
                print(f"🎨 Генерирую слайд {slide_order} для карусели {carousel_id}")
                
                # Заменяем плейсхолдеры в SVG
                processed_svg = replace_svg_placeholders(svg_content, replacements_json)
                
                # Создаем путь для выходного файла
                output_dir = os.path.join(OUTPUT_FOLDER, carousel_id)
                output_filename = f"slide_{slide_order}.png"
                output_path = os.path.join(output_dir, output_filename)
                
                # Генерируем PNG
                if generate_png_from_svg(processed_svg, output_path):
                    # Создаем URL для доступа к файлу
                    output_url = f"/output/{carousel_id}/{output_filename}"
                    
                    cursor.execute('''
                        UPDATE carousel_slides 
                        SET output_url = ?, status = 'completed'
                        WHERE id = ?
                    ''', (output_url, slide_id))
                    
                    print(f"✅ Слайд {slide_order} сгенерирован: {output_url}")
                else:
                    cursor.execute('''
                        UPDATE carousel_slides 
                        SET status = 'error'
                        WHERE id = ?
                    ''', (slide_id,))
                    
            except Exception as slide_error:
                print(f"❌ Ошибка генерации слайда {slide_order}: {slide_error}")
                cursor.execute('''
                    UPDATE carousel_slides 
                    SET status = 'error'
                    WHERE id = ?
                ''', (slide_id,))
        
        # Обновляем статус карусели на "completed"
        cursor.execute('''
            UPDATE carousels 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (carousel_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'carouselId': carousel_id,
            'status': 'completed',
            'message': 'Carousel generation completed'
        })
        
    except Exception as e:
        print(f"❌ Ошибка генерации карусели: {e}")
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE carousels 
            SET status = 'error', error_message = ?
            WHERE id = ?
        ''', (str(e), carousel_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/carousel/<carousel_id>/slides', methods=['GET'])
def get_carousel_slides(carousel_id):
    """Получить результаты генерации карусели"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Получаем информацию о карусели
        cursor.execute('''
            SELECT id, name, status, created_at, completed_at, error_message
            FROM carousels WHERE id = ?
        ''', (carousel_id,))
        
        carousel_info = cursor.fetchone()
        
        if not carousel_info:
            return jsonify({
                'success': False,
                'error': 'Carousel not found'
            }), 404
        
        carousel_id, name, status, created_at, completed_at, error_message = carousel_info
        
        # Получаем слайды
        cursor.execute('''
            SELECT id, template_id, output_url, status, slide_order
            FROM carousel_slides 
            WHERE carousel_id = ?
            ORDER BY slide_order
        ''', (carousel_id,))
        
        slides = []
        for row in cursor.fetchall():
            slide_id, template_id, output_url, slide_status, slide_order = row
            slides.append({
                'id': slide_id,
                'templateId': template_id,
                'slideNumber': slide_order,
                'imageUrl': f"https://svg-template-api-server.onrender.com{output_url}" if output_url else None,
                'status': slide_status
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'carouselId': carousel_id,
            'name': name,
            'status': status,
            'slides': slides,
            'createdAt': created_at,
            'completedAt': completed_at,
            'errorMessage': error_message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ENDPOINT ДЛЯ СТАТИЧЕСКИХ ФАЙЛОВ С ПРАВИЛЬНЫМИ CORS
@app.route('/output/<path:filename>')
def serve_output_file(filename):
    """Отдает сгенерированные изображения с правильными CORS заголовками"""
    try:
        response = send_from_directory(OUTPUT_FOLDER, filename)
        
        # Добавляем CORS заголовки для изображений
        response.headers.add('Access-Control-Allow-Origin', 'https://agentflow-marketing-hub.vercel.app')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        
        return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'File not found: {filename}'
        }), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

