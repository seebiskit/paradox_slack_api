import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

DB_PATH = Path("data/metrics.db")

def init_database():
    """Initialize the database with required tables"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    
    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            is_template BOOLEAN DEFAULT FALSE,
            created_by_user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, created_by_user_id)
        )
    """)
    
    # Metric definitions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metric_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            units TEXT,
            description TEXT,
            validation_type TEXT DEFAULT 'number',
            min_value REAL,
            max_value REAL,
            decimal_places INTEGER DEFAULT 2,
            display_order INTEGER DEFAULT 0,
            is_required BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            UNIQUE(category_id, name)
        )
    """)
    
    # Actual metrics data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            metric_definition_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            metric_date DATE NOT NULL,
            value REAL NOT NULL,
            notes TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (metric_definition_id) REFERENCES metric_definitions(id)
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_category_date ON metrics(category_id, metric_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_user_date ON metrics(user_id, metric_date)")
    
    conn.commit()
    conn.close()

def get_connection():
    """Get a database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_category_template(name: str, description: str, icon: str, metrics: List[Dict]) -> int:
    """Create a category template with its metric definitions"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert category
        cursor.execute("""
            INSERT INTO categories (name, description, icon, is_template)
            VALUES (?, ?, ?, TRUE)
        """, (name, description, icon))
        
        category_id = cursor.lastrowid
        
        # Insert metric definitions
        for metric in metrics:
            cursor.execute("""
                INSERT INTO metric_definitions 
                (category_id, name, units, validation_type, min_value, max_value, 
                 decimal_places, display_order, is_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category_id,
                metric['name'],
                metric.get('units'),
                metric.get('validation_type', 'number'),
                metric.get('min_value'),
                metric.get('max_value'),
                metric.get('decimal_places', 2),
                metric.get('display_order', 0),
                metric.get('is_required', True)
            ))
        
        conn.commit()
        return category_id
        
    finally:
        conn.close()

def get_category_templates() -> List[Dict]:
    """Get all category templates with their metrics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM categories 
            WHERE is_template = TRUE
            ORDER BY name
        """)
        
        templates = []
        for row in cursor.fetchall():
            template = dict(row)
            
            # Get metrics for this category
            cursor.execute("""
                SELECT * FROM metric_definitions 
                WHERE category_id = ? 
                ORDER BY display_order, name
            """, (template['id'],))
            
            template['metrics'] = [dict(metric_row) for metric_row in cursor.fetchall()]
            templates.append(template)
            
        return templates
        
    finally:
        conn.close()

def get_user_categories(user_id: str) -> List[Dict]:
    """Get categories created by a specific user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM categories 
            WHERE created_by_user_id = ? AND is_template = FALSE
            ORDER BY name
        """, (user_id,))
        
        categories = []
        for row in cursor.fetchall():
            category = dict(row)
            
            # Get metrics for this category
            cursor.execute("""
                SELECT * FROM metric_definitions 
                WHERE category_id = ? 
                ORDER BY display_order, name
            """, (category['id'],))
            
            category['metrics'] = [dict(metric_row) for metric_row in cursor.fetchall()]
            categories.append(category)
            
        return categories
        
    finally:
        conn.close()

def create_category_from_template(template_id: int, user_id: str, custom_name: str = None) -> int:
    """Create a user's category instance from a template, or return existing one"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get template details
        cursor.execute("SELECT * FROM categories WHERE id = ? AND is_template = TRUE", (template_id,))
        template = cursor.fetchone()
        if not template:
            raise ValueError("Template not found")
        
        category_name = custom_name or template['name']
        
        # Check if user already has this category
        cursor.execute("""
            SELECT id FROM categories 
            WHERE name = ? AND created_by_user_id = ? AND is_template = FALSE
        """, (category_name, user_id))
        
        existing = cursor.fetchone()
        if existing:
            return existing['id']
        
        # Create user category
        cursor.execute("""
            INSERT INTO categories (name, description, icon, is_template, created_by_user_id)
            VALUES (?, ?, ?, FALSE, ?)
        """, (category_name, template['description'], template['icon'], user_id))
        
        new_category_id = cursor.lastrowid
        
        # Copy metric definitions from template
        cursor.execute("SELECT * FROM metric_definitions WHERE category_id = ?", (template_id,))
        template_metrics = cursor.fetchall()
        
        for metric in template_metrics:
            cursor.execute("""
                INSERT INTO metric_definitions 
                (category_id, name, units, validation_type, min_value, max_value, 
                 decimal_places, display_order, is_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_category_id,
                metric['name'],
                metric['units'],
                metric['validation_type'],
                metric['min_value'],
                metric['max_value'],
                metric['decimal_places'],
                metric['display_order'],
                metric['is_required']
            ))
        
        conn.commit()
        return new_category_id
        
    finally:
        conn.close()

def log_metrics(category_id: int, user_id: str, metric_date: str, 
                metric_values: List[Dict], notes: str = None) -> List[int]:
    """Log multiple metrics for a category"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        logged_ids = []
        logged_at = datetime.now(timezone.utc).isoformat()
        
        for metric_data in metric_values:
            cursor.execute("""
                INSERT INTO metrics 
                (category_id, metric_definition_id, user_id, metric_date, value, notes, logged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                category_id,
                metric_data['metric_definition_id'],
                user_id,
                metric_date,
                metric_data['value'],
                notes,
                logged_at
            ))
            logged_ids.append(cursor.lastrowid)
        
        conn.commit()
        return logged_ids
        
    finally:
        conn.close()

def get_category_with_metrics(category_id: int) -> Optional[Dict]:
    """Get a category with all its metric definitions"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get category
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        if not category:
            return None
            
        category = dict(category)
        
        # Get metrics
        cursor.execute("""
            SELECT * FROM metric_definitions 
            WHERE category_id = ? 
            ORDER BY display_order, name
        """, (category_id,))
        
        category['metrics'] = [dict(row) for row in cursor.fetchall()]
        return category
        
    finally:
        conn.close()