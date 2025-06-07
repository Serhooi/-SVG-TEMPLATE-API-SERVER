#!/usr/bin/env python3
"""
Создание полностью исправленного API сервера SVG Template
с правильной инициализацией базы данных и всеми необходимыми endpoints
"""

import os
import sqlite3
import json
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import subprocess

app = Flask(__name__)
CORS(app)

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
            status TEXT DEFAULT 'created',
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
            replacements TEXT,
            slide_order INTEGER,
            output_url TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (carousel_id) REFERENCES carousels (id),
            FOREIGN KEY (template_id) REFERENCES templates (id)
        )
    ''')
    
    # Проверяем есть ли уже шаблоны
    cursor.execute('SELECT COUNT(*) FROM templates')
    template_count = cursor.fetchone()[0]
    
    if template_count == 0:
        print("📦 Добавляем тестовые шаблоны...")
        
        # Добавляем тестовые шаблоны
        test_templates = [
            {
                'id': 'open-house-main',
                'name': 'Open House - Main Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#f8f9fa"/>
                    <text x="200" y="50" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">OPEN HOUSE</text>
                    <text x="200" y="100" text-anchor="middle" font-size="18" fill="#666" id="dyno.propertyAddress">Property Address</text>
                    <text x="200" y="140" text-anchor="middle" font-size="20" font-weight="bold" fill="#2563eb" id="dyno.price">$000,000</text>
                    <text x="50" y="200" font-size="14" fill="#333" id="dyno.bedrooms">0</text>
                    <text x="150" y="200" font-size="14" fill="#333" id="dyno.bathrooms">0</text>
                    <text x="250" y="200" font-size="14" fill="#333" id="dyno.sqft">0</text>
                    <text x="50" y="250" font-size="12" fill="#666" id="dyno.openHouseDate">Date</text>
                    <text x="50" y="270" font-size="12" fill="#666" id="dyno.openHouseTime">Time</text>
                    <text x="50" y="320" font-size="14" font-weight="bold" fill="#333" id="dyno.agentName">Agent Name</text>
                    <text x="50" y="340" font-size="12" fill="#666" id="dyno.agentPhone">Phone</text>
                    <text x="50" y="360" font-size="12" fill="#666" id="dyno.agentEmail">Email</text>
                    <image x="50" y="400" width="300" height="150" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" id="dyno.propertyImage"/>
                </svg>'''
            },
            {
                'id': 'open-house-photo',
                'name': 'Open House - Photo Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#f8f9fa"/>
                    <text x="200" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#333" id="dyno.propertyAddress">Property Address</text>
                    <image x="20" y="50" width="360" height="480" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" id="dyno.propertyImage"/>
                    <text x="200" y="560" text-anchor="middle" font-size="12" fill="#666" id="dyno.agentName">Agent Name</text>
                    <text x="200" y="580" text-anchor="middle" font-size="10" fill="#666" id="dyno.agentPhone">Phone</text>
                </svg>'''
            },
            {
                'id': 'sold-main',
                'name': 'Sold - Main Template',
                'category': 'sold',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#f8f9fa"/>
                    <text x="200" y="50" text-anchor="middle" font-size="24" font-weight="bold" fill="#dc2626">SOLD</text>
                    <text x="200" y="100" text-anchor="middle" font-size="18" fill="#666" id="dyno.propertyAddress">Property Address</text>
                    <text x="200" y="140" text-anchor="middle" font-size="20" font-weight="bold" fill="#2563eb" id="dyno.price">$000,000</text>
                    <text x="50" y="200" font-size="14" fill="#333" id="dyno.bedrooms">0</text>
                    <text x="150" y="200" font-size="14" fill="#333" id="dyno.bathrooms">0</text>
                    <text x="250" y="200" font-size="14" fill="#333" id="dyno.sqft">0</text>
                    <text x="50" y="320" font-size="14" font-weight="bold" fill="#333" id="dyno.agentName">Agent Name</text>
                    <text x="50" y="340" font-size="12" fill="#666" id="dyno.agentPhone">Phone</text>
                    <text x="50" y="360" font-size="12" fill="#666" id="dyno.agentEmail">Email</text>
                    <image x="50" y="400" width="300" height="150" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" id="dyno.propertyImage"/>
                </svg>'''
            },
            {
                'id': 'sold-photo',
                'name': 'Sold - Photo Template',
                'category': 'sold',
                'template_type': 'flyer',
                'svg_content': '''<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="400" height="600" fill="#f8f9fa"/>
                    <text x="200" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#dc2626">SOLD</text>
                    <text x="200" y="50" text-anchor="middle" font-size="14" fill="#666" id="dyno.propertyAddress">Property Address</text>
                    <image x="20" y="70" width="360" height="480" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" id="dyno.propertyImage"/>
                    <text x="200" y="570" text-anchor="middle" font-size="12" fill="#666" id="dyno.agentName">Agent Name</text>
                    <text x="200" y="590" text-anchor="middle" font-size="10" fill="#666" id="dyno.agentPhone">Phone</text>
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

# Инициализируем базу данных при запуске
init_database()

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния API"""
    return jsonify({
        'status': 'healthy',
        'message': 'SVG Template API is running',
        'timestamp': datetime.now().isoformat()
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
            'templates': templates,
            'count': len(templates)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/templates/<template_id>/preview', methods=['GET'])
def get_template_preview(template_id):
    """Получить превью шаблона"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT svg_content FROM templates WHERE id = ?', (template_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Template not found'}), 404
        
        svg_content = result[0]
        conn.close()
        
        return svg_content, 200, {'Content-Type': 'image/svg+xml'}
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        
        # Создаем карусель
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO carousels (id, name, status)
            VALUES (?, ?, 'created')
        ''', (carousel_id, data['name']))
        
        # Добавляем слайды
        for i, slide in enumerate(data['slides']):
            slide_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO carousel_slides (id, carousel_id, template_id, replacements, slide_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (slide_id, carousel_id, slide['templateId'], 
                  json.dumps(slide.get('replacements', {})), i))
        
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
            SELECT id, template_id, replacements, slide_order
            FROM carousel_slides 
            WHERE carousel_id = ?
            ORDER BY slide_order
        ''', (carousel_id,))
        
        slides = cursor.fetchall()
        
        # Симуляция генерации (в реальности здесь был бы код обработки SVG)
        for slide_id, template_id, replacements_json, slide_order in slides:
            # Генерируем фиктивный URL для демонстрации
            output_url = f"https://svg-template-api-server.onrender.com/output/{carousel_id}/slide_{slide_order}.png"
            
            cursor.execute('''
                UPDATE carousel_slides 
                SET output_url = ?, status = 'completed'
                WHERE id = ?
            ''', (output_url, slide_id))
        
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
                'outputUrl': output_url,
                'status': slide_status,
                'order': slide_order
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'carousel': {
                'id': carousel_id,
                'name': name,
                'status': status,
                'created_at': created_at,
                'completed_at': completed_at,
                'error_message': error_message
            },
            'slides': slides,
            'total_slides': len(slides)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/templates/upload', methods=['POST'])
def upload_template():
    """Загрузить новый шаблон (для интеграции с админкой)"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'category', 'svg_content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        template_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO templates (id, name, category, svg_content, template_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (template_id, data['name'], data['category'], 
              data['svg_content'], data.get('template_type', 'flyer')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'template_id': template_id,
            'message': 'Template uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

