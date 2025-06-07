from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
import json
import uuid
import base64
from io import BytesIO
from PIL import Image
import xml.etree.ElementTree as ET
import re
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app, origins="*")

# Конфигурация
DATABASE = 'templates.db'
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'

# Создать необходимые папки
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Хранилище для статуса генерации
generation_status = {}

def init_db():
    """Инициализация базы данных с проверкой существования"""
    print("🔧 Инициализация базы данных...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Проверить существование таблицы templates
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='templates'
    """)
    
    if not cursor.fetchone():
        print("📋 Создаю таблицу templates...")
        # Создать таблицу шаблонов
        cursor.execute("""
            CREATE TABLE templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                template_type TEXT NOT NULL,
                template_role TEXT NOT NULL,
                svg_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавить тестовые шаблоны
        test_templates = [
            {
                'id': 'open-house-main',
                'name': 'Open House Main Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'template_role': 'main',
                'svg_content': """<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="800" height="600" fill="#f0f0f0"/>
                    <text x="400" y="100" text-anchor="middle" font-size="24" fill="#333">dyno.propertyAddress</text>
                    <text x="400" y="150" text-anchor="middle" font-size="18" fill="#666">dyno.price</text>
                    <text x="400" y="200" text-anchor="middle" font-size="16" fill="#666">dyno.bedrooms bed, dyno.bathrooms bath</text>
                    <text x="400" y="500" text-anchor="middle" font-size="14" fill="#333">dyno.agentName - dyno.agentPhone</text>
                    <image x="50" y="250" width="300" height="200" href="dyno.propertyImage"/>
                    <image x="450" y="450" width="100" height="100" href="dyno.agentheadshot"/>
                    <image x="600" y="450" width="150" height="50" href="dyno.logo"/>
                </svg>"""
            },
            {
                'id': 'open-house-photo',
                'name': 'Open House Photo Template',
                'category': 'open-house',
                'template_type': 'flyer',
                'template_role': 'photo',
                'svg_content': """<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="800" height="600" fill="#ffffff"/>
                    <image x="0" y="0" width="800" height="600" href="dyno.propertyImage"/>
                </svg>"""
            },
            {
                'id': 'sold-main',
                'name': 'Sold Main Template',
                'category': 'sold',
                'template_type': 'flyer',
                'template_role': 'main',
                'svg_content': """<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="800" height="600" fill="#e8f5e8"/>
                    <text x="400" y="80" text-anchor="middle" font-size="32" fill="#d32f2f" font-weight="bold">SOLD</text>
                    <text x="400" y="130" text-anchor="middle" font-size="24" fill="#333">dyno.propertyAddress</text>
                    <text x="400" y="170" text-anchor="middle" font-size="18" fill="#666">dyno.price</text>
                    <text x="400" y="220" text-anchor="middle" font-size="16" fill="#666">dyno.bedrooms bed, dyno.bathrooms bath</text>
                    <text x="400" y="520" text-anchor="middle" font-size="14" fill="#333">dyno.agentName - dyno.agentPhone</text>
                    <image x="50" y="270" width="300" height="200" href="dyno.propertyImage"/>
                    <image x="450" y="470" width="100" height="100" href="dyno.agentheadshot"/>
                    <image x="600" y="470" width="150" height="50" href="dyno.logo"/>
                </svg>"""
            },
            {
                'id': 'sold-photo',
                'name': 'Sold Photo Template',
                'category': 'sold',
                'template_type': 'flyer',
                'template_role': 'photo',
                'svg_content': """<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
                    <rect width="800" height="600" fill="#ffffff"/>
                    <image x="0" y="0" width="800" height="600" href="dyno.propertyImage"/>
                    <rect x="300" y="50" width="200" height="60" fill="#d32f2f" opacity="0.9"/>
                    <text x="400" y="90" text-anchor="middle" font-size="28" fill="white" font-weight="bold">SOLD</text>
                </svg>"""
            }
        ]
        
        for template in test_templates:
            cursor.execute("""
                INSERT INTO templates (id, name, category, template_type, template_role, svg_content)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                template['id'],
                template['name'],
                template['category'],
                template['template_type'],
                template['template_role'],
                template['svg_content']
            ))
        
        print(f"✅ Добавлено {len(test_templates)} тестовых шаблонов")
    else:
        print("✅ Таблица templates уже существует")
    
    # Проверить существование таблицы carousels
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='carousels'
    """)
    
    if not cursor.fetchone():
        print("📋 Создаю таблицу carousels...")
        # Создать таблицу каруселей
        cursor.execute("""
            CREATE TABLE carousels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                slides_data TEXT,
                output_urls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Таблица carousels создана")
    else:
        print("✅ Таблица carousels уже существует")
    
    conn.commit()
    conn.close()
    print("🎉 База данных инициализирована успешно!")

def get_db_connection():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def process_svg_replacements(svg_content, replacements, images=None):
    """Обработать замены в SVG"""
    try:
        # Парсинг SVG
        root = ET.fromstring(svg_content)
        
        # Замена текста
        for element in root.iter():
            if element.text and any(key in element.text for key in replacements.keys()):
                for key, value in replacements.items():
                    if key in element.text:
                        element.text = element.text.replace(key, str(value))
        
        # Замена изображений
        if images:
            for element in root.iter():
                if element.tag.endswith('image'):
                    href = element.get('{http://www.w3.org/1999/xlink}href') or element.get('href')
                    if href and 'dyno.' in href:
                        # Найти соответствующее изображение
                        for img_key, img_data in images.items():
                            if img_key in href:
                                element.set('{http://www.w3.org/1999/xlink}href', img_data)
                                break
        
        return ET.tostring(root, encoding='unicode')
    except Exception as e:
        print(f"Ошибка обработки SVG: {e}")
        return svg_content

def svg_to_png(svg_content, output_path, width=800, height=600):
    """Конвертировать SVG в PNG"""
    try:
        from cairosvg import svg2png
        
        svg2png(
            bytestring=svg_content.encode('utf-8'),
            write_to=output_path,
            output_width=width,
            output_height=height
        )
        return True
    except Exception as e:
        print(f"Ошибка конвертации SVG в PNG: {e}")
        return False

def generate_carousel_async(carousel_id, slides_data):
    """Асинхронная генерация карусели"""
    try:
        generation_status[carousel_id] = {'status': 'processing', 'progress': 0}
        
        conn = get_db_connection()
        output_urls = []
        
        for i, slide in enumerate(slides_data):
            # Обновить прогресс
            progress = int((i / len(slides_data)) * 100)
            generation_status[carousel_id]['progress'] = progress
            
            # Получить шаблон
            template = conn.execute(
                'SELECT svg_content FROM templates WHERE id = ?',
                (slide['templateId'],)
            ).fetchone()
            
            if not template:
                continue
            
            # Обработать замены
            processed_svg = process_svg_replacements(
                template['svg_content'],
                slide.get('replacements', {}),
                slide.get('images', {})
            )
            
            # Сгенерировать PNG
            output_filename = f"{carousel_id}_slide_{i+1}.png"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            if svg_to_png(processed_svg, output_path):
                output_urls.append(f"/api/carousel/{carousel_id}/slide/{i+1}")
        
        # Обновить статус в базе данных
        conn.execute(
            'UPDATE carousels SET status = ?, output_urls = ? WHERE id = ?',
            ('completed', json.dumps(output_urls), carousel_id)
        )
        conn.commit()
        conn.close()
        
        generation_status[carousel_id] = {
            'status': 'completed',
            'progress': 100,
            'urls': output_urls
        }
        
    except Exception as e:
        print(f"Ошибка генерации карусели: {e}")
        generation_status[carousel_id] = {
            'status': 'error',
            'error': str(e)
        }

# API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'message': 'SVG Template API is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/templates/all-previews', methods=['GET'])
def get_all_templates_with_previews():
    """Получить все шаблоны с превью"""
    try:
        conn = get_db_connection()
        templates = conn.execute("""
            SELECT id, name, category, template_type, template_role
            FROM templates
            ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        
        result = []
        for template in templates:
            result.append({
                'id': template['id'],
                'name': template['name'],
                'category': template['category'],
                'template_type': template['template_type'],
                'template_role': template['template_role'],
                'preview_url': f'/api/templates/{template["id"]}/preview'
            })
        
        return jsonify({
            'success': True,
            'templates': result
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
        conn = get_db_connection()
        template = conn.execute(
            'SELECT svg_content FROM templates WHERE id = ?',
            (template_id,)
        ).fetchone()
        conn.close()
        
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        # Генерировать превью PNG
        preview_path = os.path.join(OUTPUT_FOLDER, f"{template_id}_preview.png")
        
        if not os.path.exists(preview_path):
            if not svg_to_png(template['svg_content'], preview_path):
                return jsonify({'error': 'Failed to generate preview'}), 500
        
        return send_file(preview_path, mimetype='image/png')
        
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
        
        # Сохранить в базу данных
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO carousels (id, name, slides_data) VALUES (?, ?, ?)',
            (carousel_id, data['name'], json.dumps(data['slides']))
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'carouselId': carousel_id,
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
        conn = get_db_connection()
        carousel = conn.execute(
            'SELECT slides_data FROM carousels WHERE id = ?',
            (carousel_id,)
        ).fetchone()
        
        if not carousel:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Carousel not found'
            }), 404
        
        slides_data = json.loads(carousel['slides_data'])
        conn.close()
        
        # Запустить асинхронную генерацию
        thread = threading.Thread(
            target=generate_carousel_async,
            args=(carousel_id, slides_data)
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Generation started',
            'carouselId': carousel_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/carousel/<carousel_id>/slides', methods=['GET'])
def get_carousel_slides(carousel_id):
    """Получить слайды карусели"""
    try:
        # Проверить статус генерации
        if carousel_id in generation_status:
            status = generation_status[carousel_id]
            if status['status'] == 'processing':
                return jsonify({
                    'success': True,
                    'status': 'processing',
                    'progress': status['progress']
                })
            elif status['status'] == 'completed':
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'slides': status['urls']
                })
            elif status['status'] == 'error':
                return jsonify({
                    'success': False,
                    'error': status['error']
                }), 500
        
        # Проверить в базе данных
        conn = get_db_connection()
        carousel = conn.execute(
            'SELECT status, output_urls FROM carousels WHERE id = ?',
            (carousel_id,)
        ).fetchone()
        conn.close()
        
        if not carousel:
            return jsonify({
                'success': False,
                'error': 'Carousel not found'
            }), 404
        
        if carousel['status'] == 'completed' and carousel['output_urls']:
            urls = json.loads(carousel['output_urls'])
            return jsonify({
                'success': True,
                'status': 'completed',
                'slides': urls
            })
        
        return jsonify({
            'success': True,
            'status': carousel['status']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/carousel/<carousel_id>/slide/<int:slide_number>', methods=['GET'])
def get_carousel_slide(carousel_id, slide_number):
    """Получить конкретный слайд карусели"""
    try:
        slide_path = os.path.join(OUTPUT_FOLDER, f"{carousel_id}_slide_{slide_number}.png")
        
        if not os.path.exists(slide_path):
            return jsonify({'error': 'Slide not found'}), 404
        
        return send_file(slide_path, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
