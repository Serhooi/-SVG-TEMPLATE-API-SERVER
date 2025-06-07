

# НОВЫЕ ENDPOINTS ДЛЯ ИНТЕГРАЦИИ С АДМИНКОЙ

@app.route('/api/templates/upload', methods=['POST'])
def upload_template():
    """Endpoint для загрузки новых шаблонов из админки"""
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['id', 'name', 'category', 'template_type', 'template_role', 'svg_content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Проверить что шаблон с таким ID не существует
        conn = get_db_connection()
        existing = conn.execute(
            'SELECT id FROM templates WHERE id = ?',
            (data['id'],)
        ).fetchone()
        
        if existing:
            # Обновить существующий шаблон
            conn.execute("""
                UPDATE templates 
                SET name = ?, category = ?, template_type = ?, 
                    template_role = ?, svg_content = ?
                WHERE id = ?
            """, (
                data['name'],
                data['category'],
                data['template_type'],
                data['template_role'],
                data['svg_content'],
                data['id']
            ))
            message = 'Template updated successfully'
        else:
            # Создать новый шаблон
            conn.execute("""
                INSERT INTO templates (id, name, category, template_type, template_role, svg_content)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['id'],
                data['name'],
                data['category'],
                data['template_type'],
                data['template_role'],
                data['svg_content']
            ))
            message = 'Template created successfully'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message,
            'template_id': data['id']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/templates/sync', methods=['POST'])
def sync_templates():
    """Синхронизация всех шаблонов из админки"""
    try:
        data = request.get_json()
        
        if 'templates' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing templates array'
            }), 400
        
        conn = get_db_connection()
        synced_count = 0
        
        for template in data['templates']:
            # Проверить обязательные поля
            required_fields = ['id', 'name', 'category', 'template_type', 'template_role', 'svg_content']
            if not all(field in template for field in required_fields):
                continue
            
            # Проверить существование
            existing = conn.execute(
                'SELECT id FROM templates WHERE id = ?',
                (template['id'],)
            ).fetchone()
            
            if existing:
                # Обновить
                conn.execute("""
                    UPDATE templates 
                    SET name = ?, category = ?, template_type = ?, 
                        template_role = ?, svg_content = ?
                    WHERE id = ?
                """, (
                    template['name'],
                    template['category'],
                    template['template_type'],
                    template['template_role'],
                    template['svg_content'],
                    template['id']
                ))
            else:
                # Создать
                conn.execute("""
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
            
            synced_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Synced {synced_count} templates',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
