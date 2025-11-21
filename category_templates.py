from database import create_category_template, init_database

CATEGORY_TEMPLATES = [
    {
        "name": "9 AM Sermon Attendance",
        "description": "Early service attendance",
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
                "name": "Total",
                "units": "people",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 3,
                "is_required": False
            }
        ]
    },
    {
        "name": "11 AM Sermon Attendance",
        "description": "Early service attendance",
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
                "name": "Total",
                "units": "people",
                "validation_type": "integer",
                "min_value": 0,
                "display_order": 3,
                "is_required": False
            }
        ]
    }
]

def setup_default_templates():
    """Initialize the database and create default templates if they don't exist"""
    init_database()
    
    # Check if templates already exist
    # why is import here?
    from database import get_category_templates
    existing_templates = get_category_templates()
    existing_names = {template['name'] for template in existing_templates}
    
    # Create missing templates
    for template in CATEGORY_TEMPLATES:
        if template['name'] not in existing_names:
            print(f"Creating template: {template['name']}")
            create_category_template(
                template['name'],
                template['description'], 
                template['icon'],
                template['metrics']
            )
        else:
            print(f"Template already exists: {template['name']}")

if __name__ == "__main__":
    setup_default_templates()
    print("Template setup complete!")