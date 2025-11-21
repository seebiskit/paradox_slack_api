Excellent! This is a much more sophisticated data model that handles real-world use cases better. Let me redesign the architecture:
Revised Data Model
Conceptual Hierarchy
Category (e.g., "Event A Attendance")
  ├─ Metric 1 (e.g., "Adults")
  ├─ Metric 2 (e.g., "Children")
  └─ Metric 3 (e.g., "Volunteers")
Database Schema
sql-- Categories are the high-level grouping
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    is_template BOOLEAN DEFAULT FALSE, -- TRUE for predefined templates
    created_by_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, created_by_user_id) -- Users can have their own version of same-named categories
);

-- Metric definitions within a category
CREATE TABLE metric_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL, -- e.g., "Adults", "Children"
    units TEXT,
    description TEXT,
    validation_type TEXT, -- 'number', 'integer', 'positive_only'
    min_value REAL,
    max_value REAL,
    decimal_places INTEGER DEFAULT 2,
    display_order INTEGER DEFAULT 0, -- For ordering in the form
    is_required BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(category_id, name)
);

-- Actual logged metric values
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    metric_definition_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    metric_date DATE NOT NULL, -- User-selectable date
    value REAL NOT NULL,
    notes TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When they actually submitted
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (metric_definition_id) REFERENCES metric_definitions(id)
);

-- Index for common queries
CREATE INDEX idx_metrics_category_date ON metrics(category_id, metric_date);
CREATE INDEX idx_metrics_user_date ON metrics(user_id, metric_date);
Predefined Category Templates
pythonCATEGORY_TEMPLATES = [
    {
        "name": "Event Attendance",
        "description": "Track attendance at events",
        "icon": "👥",
        "metrics": [
            {
                "name": "Adults",
                "units": "people",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 1
            },
            {
                "name": "Children",
                "units": "people",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 2
            },
            {
                "name": "Volunteers",
                "units": "people",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 3,
                "is_required": False
            }
        ]
    },
    {
        "name": "Daily Vitals",
        "description": "Track health measurements",
        "icon": "❤️",
        "metrics": [
            {
                "name": "Weight",
                "units": "lbs",
                "validation_type": "positive_only",
                "decimal_places": 1,
                "display_order": 1
            },
            {
                "name": "Blood Pressure (Systolic)",
                "units": "mmHg",
                "validation_type": "integer",
                "min_value": 60,
                "max_value": 200,
                "display_order": 2
            },
            {
                "name": "Blood Pressure (Diastolic)",
                "units": "mmHg",
                "validation_type": "integer",
                "min_value": 40,
                "max_value": 130,
                "display_order": 3
            },
            {
                "name": "Resting Heart Rate",
                "units": "bpm",
                "validation_type": "integer",
                "min_value": 40,
                "max_value": 200,
                "display_order": 4,
                "is_required": False
            }
        ]
    },
    {
        "name": "Sales Metrics",
        "description": "Daily sales tracking",
        "icon": "💰",
        "metrics": [
            {
                "name": "Revenue",
                "units": "$",
                "validation_type": "number",
                "decimal_places": 2,
                "min_value": 0,
                "display_order": 1
            },
            {
                "name": "Transactions",
                "units": "count",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 2
            },
            {
                "name": "New Customers",
                "units": "count",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 3,
                "is_required": False
            }
        ]
    },
    {
        "name": "Workout",
        "description": "Track exercise sessions",
        "icon": "💪",
        "metrics": [
            {
                "name": "Duration",
                "units": "minutes",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 1
            },
            {
                "name": "Calories Burned",
                "units": "kcal",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 2,
                "is_required": False
            },
            {
                "name": "Distance",
                "units": "miles",
                "validation_type": "number",
                "decimal_places": 2,
                "min_value": 0,
                "display_order": 3,
                "is_required": False
            }
        ]
    },
    {
        "name": "Simple Tracker",
        "description": "Single metric tracking",
        "icon": "📊",
        "metrics": [
            {
                "name": "Value",
                "units": "",
                "validation_type": "number",
                "decimal_places": 2,
                "display_order": 1
            }
        ]
    }
]
Updated Slack Modal Flow
pythondef build_log_metric_modal(user_categories, category_templates):
    """
    Step 1: User selects a category (from templates or their existing categories)
    """
    options = []
    
    # Group templates by type
    options.append({
        "text": {"type": "plain_text", "text": "── Templates ──"},
        "value": "header_templates"
    })
    
    for template in category_templates:
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{template['icon']} {template['name']}"
            },
            "value": f"template_{template['id']}"
        })
    
    # Add user's existing categories
    if user_categories:
        options.append({
            "text": {"type": "plain_text", "text": "── My Categories ──"},
            "value": "header_mine"
        })
        
        for category in user_categories:
            options.append({
                "text": {"type": "plain_text", "text": f"{category['icon']} {category['name']}"},
                "value": f"category_{category['id']}"
            })
    
    # Create new option
    options.append({
        "text": {"type": "plain_text", "text": "➕ Create New Category..."},
        "value": "create_new"
    })
    
    return {
        "type": "modal",
        "callback_id": "select_category_modal",
        "title": {"type": "plain_text", "text": "Log Metrics"},
        "blocks": [
            {
                "type": "input",
                "block_id": "category_select",
                "element": {
                    "type": "static_select",
                    "action_id": "category_selection",
                    "placeholder": {"type": "plain_text", "text": "Choose a category..."},
                    "options": options
                },
                "label": {"type": "plain_text", "text": "Category"}
            }
        ],
        "submit": {"type": "plain_text", "text": "Next"}
    }


def build_metric_entry_modal(category_id, metric_definitions):
    """
    Step 2: After category selection, show form with all metrics in that category
    Plus date selector at the top
    """
    from datetime import date
    
    blocks = [
        # Date picker at the top
        {
            "type": "input",
            "block_id": "metric_date",
            "element": {
                "type": "datepicker",
                "action_id": "date_selection",
                "initial_date": date.today().isoformat(),
                "placeholder": {"type": "plain_text", "text": "Select date"}
            },
            "label": {"type": "plain_text", "text": "📅 Metric Date"}
        },
        {
            "type": "divider"
        }
    ]
    
    # Add input for each metric definition
    for metric_def in sorted(metric_definitions, key=lambda x: x['display_order']):
        label_text = metric_def['name']
        if metric_def['units']:
            label_text += f" ({metric_def['units']})"
        if not metric_def['is_required']:
            label_text += " (optional)"
        
        placeholder_text = f"Enter {metric_def['name'].lower()}"
        if metric_def.get('min_value') is not None and metric_def.get('max_value') is not None:
            placeholder_text += f" ({metric_def['min_value']}-{metric_def['max_value']})"
        
        blocks.append({
            "type": "input",
            "block_id": f"metric_{metric_def['id']}",
            "optional": not metric_def['is_required'],
            "element": {
                "type": "plain_text_input",
                "action_id": f"value_{metric_def['id']}",
                "placeholder": {"type": "plain_text", "text": placeholder_text}
            },
            "label": {"type": "plain_text", "text": label_text}
        })
    
    # Optional notes field
    blocks.append({
        "type": "input",
        "block_id": "notes",
        "optional": True,
        "element": {
            "type": "plain_text_input",
            "action_id": "notes_input",
            "multiline": True,
            "placeholder": {"type": "plain_text", "text": "Add any notes..."}
        },
        "label": {"type": "plain_text", "text": "📝 Notes"}
    })
    
    return {
        "type": "modal",
        "callback_id": "log_metrics_modal",
        "title": {"type": "plain_text", "text": "Log Metrics"},
        "private_metadata": str(category_id),  # Pass category_id through
        "blocks": blocks,
        "submit": {"type": "plain_text", "text": "Log All"}
    }
API Endpoints
pythonfrom fastapi import FastAPI, HTTPException
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()

# Models
class MetricDefinition(BaseModel):
    name: str
    units: Optional[str] = None
    validation_type: str = "number"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    decimal_places: int = 2
    display_order: int = 0
    is_required: bool = True

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = "📊"
    metrics: List[MetricDefinition]

class MetricLogEntry(BaseModel):
    metric_definition_id: int
    value: float

class MetricsLog(BaseModel):
    category_id: int
    metric_date: date
    metrics: List[MetricLogEntry]
    notes: Optional[str] = None

# Endpoints
@app.get("/api/category-templates")
async def get_category_templates():
    """Get all predefined category templates"""
    query = """
        SELECT c.*, 
               json_group_array(
                   json_object(
                       'id', m.id,
                       'name', m.name,
                       'units', m.units,
                       'validation_type', m.validation_type,
                       'min_value', m.min_value,
                       'max_value', m.max_value,
                       'decimal_places', m.decimal_places,
                       'display_order', m.display_order,
                       'is_required', m.is_required
                   )
               ) as metrics
        FROM categories c
        LEFT JOIN metric_definitions m ON c.id = m.category_id
        WHERE c.is_template = TRUE
        GROUP BY c.id
        ORDER BY c.name
    """
    return db.execute(query).fetchall()

@app.get("/api/categories/user/{user_id}")
async def get_user_categories(user_id: str):
    """Get categories created by user"""
    query = """
        SELECT c.*, 
               json_group_array(
                   json_object(
                       'id', m.id,
                       'name', m.name,
                       'units', m.units,
                       'validation_type', m.validation_type,
                       'display_order', m.display_order,
                       'is_required', m.is_required
                   )
               ) as metrics
        FROM categories c
        LEFT JOIN metric_definitions m ON c.id = m.category_id
        WHERE c.created_by_user_id = ? AND c.is_template = FALSE
        GROUP BY c.id
        ORDER BY c.name
    """
    return db.execute(query, [user_id]).fetchall()

@app.post("/api/categories/from-template")
async def create_category_from_template(
    template_id: int,
    user_id: str,
    custom_name: Optional[str] = None
):
    """Create a user's category instance from a template"""
    # Copy template to user's categories
    # Copy all metric_definitions
    pass

@app.post("/api/categories")
async def create_custom_category(category: CategoryCreate, user_id: str):
    """Create a completely custom category"""
    # Insert category
    # Insert all metric definitions
    pass

@app.post("/api/metrics/log")
async def log_metrics(log_data: MetricsLog, user_id: str):
    """
    Log multiple metrics for a category at once
    Creates one row per metric in the metrics table
    """
    category_id = log_data.category_id
    metric_date = log_data.metric_date
    notes = log_data.notes
    
    rows_inserted = []
    
    for metric_entry in log_data.metrics:
        query = """
            INSERT INTO metrics 
            (category_id, metric_definition_id, user_id, metric_date, value, notes, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor = db.execute(
            query,
            [
                category_id,
                metric_entry.metric_definition_id,
                user_id,
                metric_date,
                metric_entry.value,
                notes,
                datetime.now()
            ]
        )
        rows_inserted.append(cursor.lastrowid)
    
    db.commit()
    
    return {
        "success": True,
        "metrics_logged": len(rows_inserted),
        "metric_ids": rows_inserted
    }

@app.get("/api/metrics/category/{category_id}")
async def get_category_metrics(
    category_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get all metrics for a category within date range"""
    query = """
        SELECT m.*, md.name as metric_name, md.units
        FROM metrics m
        JOIN metric_definitions md ON m.metric_definition_id = md.id
        WHERE m.category_id = ?
    """
    params = [category_id]
    
    if start_date:
        query += " AND m.metric_date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND m.metric_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY m.metric_date DESC, md.display_order ASC"
    
    return db.execute(query, params).fetchall()
CSV Export Format
When exporting to CSV, each row represents one logged metric:
csvcategory_name,metric_name,metric_date,value,units,notes,user_id,logged_at
Event A Attendance,Adults,2025-11-16,45,people,"Great turnout!",U12345,2025-11-16 14:30:00
Event A Attendance,Children,2025-11-16,23,people,"Great turnout!",U12345,2025-11-16 14:30:00
Event A Attendance,Volunteers,2025-11-16,8,people,"Great turnout!",U12345,2025-11-16 14:30:00
Daily Vitals,Weight,2025-11-16,185.2,lbs,,U12345,2025-11-16 07:15:00
Daily Vitals,Blood Pressure (Systolic),2025-11-16,120,mmHg,,U12345,2025-11-16 07:15:00
This gives you maximum flexibility for analysis - you can easily:

Filter by category
Plot individual metrics over time
Compare metrics within a category
Aggregate by date or user