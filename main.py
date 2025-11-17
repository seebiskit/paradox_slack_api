from flask import Flask, request, jsonify
import os, requests, sys, json, csv
from pathlib import Path
from datetime import datetime, timezone, date
from database import (
    init_database, get_category_templates, get_user_categories, 
    get_category_with_metrics, create_category_from_template, log_metrics
)
from category_templates import setup_default_templates

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize database and templates on startup
setup_default_templates()

CSV_PATH = Path("data/metrics.csv")

def append_metric_rows(category_name: str, user_id: str, metric_date: str, 
                      metric_entries: list, notes: str = None):
    """Append multiple metric rows to CSV (one per metric)"""
    new_file = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["category_name", "metric_name", "metric_date", 
                           "value", "units", "notes", "user_id", "logged_at"])
        
        logged_at = datetime.now(timezone.utc).isoformat()
        for entry in metric_entries:
            writer.writerow([
                category_name,
                entry['metric_name'],
                metric_date,
                entry['value'],
                entry['units'] or '',
                notes or '',
                user_id,
                logged_at
            ])


def build_category_selection_modal(user_id: str):
    """Build the category selection modal"""
    user_categories = get_user_categories(user_id)
    
    options = []
    
    # Only show user's existing categories
    for category in user_categories:
        options.append({
            "text": {"type": "plain_text", "text": f"{category['icon']} {category['name']}"},
            "value": f"category_{category['id']}"
        })
    
    # Sort all options alphabetically by display text
    options.sort(key=lambda x: x["text"]["text"])
    
    blocks = [
        {
            "type": "input",
            "block_id": "category_select",
            "element": {
                "type": "static_select",
                "action_id": "category_selection",
                "placeholder": {"type": "plain_text", "text": "Choose or type to search..."},
                "options": options
            },
            "label": {"type": "plain_text", "text": "Category"}
        }
    ]
    
    # Add create category button if user has categories or always show it
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "action_id": "create_category_button",
                "text": {"type": "plain_text", "text": "➕ Create New Category"},
                "style": "primary"
            }
        ]
    })
    
    return {
        "type": "modal",
        "callback_id": "select_category_modal",
        "title": {"type": "plain_text", "text": "Log Metrics"},
        "blocks": blocks,
        "submit": {"type": "plain_text", "text": "Next"}
    }

def build_create_category_modal():
    """Build the create category modal with template selection"""
    templates = get_category_templates()
    
    options = []
    
    # Add all available templates
    for template in templates:
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{template['icon']} {template['name']}"
            },
            "value": f"template_{template['id']}"
        })
    
    return {
        "type": "modal",
        "callback_id": "create_category_modal",
        "title": {"type": "plain_text", "text": "Create Category"},
        "blocks": [
            {
                "type": "input",
                "block_id": "template_select",
                "element": {
                    "type": "static_select",
                    "action_id": "template_selection",
                    "placeholder": {"type": "plain_text", "text": "Choose a template..."},
                    "options": options
                },
                "label": {"type": "plain_text", "text": "Template"}
            },
            {
                "type": "input",
                "block_id": "category_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "Enter custom name (optional)"}
                },
                "label": {"type": "plain_text", "text": "Category Name"},
                "optional": True
            }
        ],
        "submit": {"type": "plain_text", "text": "Create Category"}
    }

@app.post("/slack/commands")
def handle_slash_command():
    trigger_id = request.form.get("trigger_id")
    user_id = request.form.get("user_id")
    
    modal = build_category_selection_modal(user_id)

    resp = requests.post(
        "https://slack.com/api/views.open",
        headers={
            "Authorization": f"Bearer {BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "trigger_id": trigger_id,
            "view": modal
        },
    )

    print("views.open status:", resp.status_code, file=sys.stderr)
    print("views.open body:", resp.text, file=sys.stderr)

    # Return empty response after successfully opening modal
    if resp.status_code == 200:
        return "", 200
    else:
        return jsonify(response_type="ephemeral", text="Error opening modal")


def build_metric_entry_modal(category_id: int, category_name: str, metric_definitions: list):
    """Build the metric entry modal for a specific category"""
    
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
    
    # Keep title under 25 characters
    if len(category_name) > 20:
        title = f"Log {category_name[:16]}..."
    else:
        title = f"Log {category_name}"
    
    return {
        "type": "modal",
        "callback_id": "log_metrics_modal",
        "title": {"type": "plain_text", "text": title},
        "private_metadata": str(category_id),
        "blocks": blocks,
        "submit": {"type": "plain_text", "text": "Log All"}
    }

@app.post("/slack/interactions")
def handle_interactions():
    payload_raw = request.form.get("payload")
    if not payload_raw:
        return "", 200

    payload = json.loads(payload_raw)
    user_id = payload.get("user", {}).get("id", "unknown")

    # Handle create category button click
    if payload.get("type") == "block_actions":
        print(f"Block action received: {json.dumps(payload, indent=2)}", file=sys.stderr)
        action = payload["actions"][0]
        print(f"Action ID: {action.get('action_id')}", file=sys.stderr)
        if action["action_id"] == "create_category_button":
            print("Creating category modal...", file=sys.stderr)
            create_modal = build_create_category_modal()
            print(f"Category modal created: {json.dumps(create_modal, indent=2)}", file=sys.stderr)
            return jsonify({
                "response_action": "push",
                "view": create_modal
            })

    # Handle create category form submission
    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "create_category_modal":
        
        state_values = payload["view"]["state"]["values"]
        
        # Get template selection
        template_selection = state_values["template_select"]["template_selection"]["selected_option"]["value"]
        template_id = int(template_selection.split("_")[1])
        
        # Get custom name if provided
        custom_name = None
        if "category_name" in state_values and state_values["category_name"]["name_input"]["value"]:
            custom_name = state_values["category_name"]["name_input"]["value"].strip()
        
        # Create category from template
        try:
            category_id = create_category_from_template(template_id, user_id, custom_name)
            print(f"Created category {category_id} for user {user_id}", file=sys.stderr)
            
            # After creating category, redirect to metric entry modal
            category_data = get_category_with_metrics(category_id)
            if category_data:
                metric_modal = build_metric_entry_modal(
                    category_id, 
                    category_data['name'], 
                    category_data['metrics']
                )
                
                return jsonify({
                    "response_action": "update",
                    "view": metric_modal
                })
        except Exception as e:
            print(f"Error creating category: {e}", file=sys.stderr)
            return jsonify({
                "response_action": "errors",
                "errors": {
                    "category_name": "Failed to create category. It may already exist."
                }
            })

    # Handle category selection
    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "select_category_modal":

        state_values = payload["view"]["state"]["values"]
        selection = state_values["category_select"]["category_selection"]["selected_option"]["value"]
        
        print(f"Category selection: {selection}", file=sys.stderr)
        
        category_id = None
        
        # Only handle existing user categories
        if selection.startswith("category_"):
            category_id = int(selection.split("_")[1])
        
        if category_id:
            # Get category details and show metrics modal
            category_data = get_category_with_metrics(category_id)
            print(f"Category data: {category_data}", file=sys.stderr)
            if category_data:
                metric_modal = build_metric_entry_modal(
                    category_id, 
                    category_data['name'], 
                    category_data['metrics']
                )
                print(f"Built metric modal for category: {category_data['name']}", file=sys.stderr)
                
                # Return the response that tells Slack to push a new view
                return jsonify({
                    "response_action": "push",
                    "view": metric_modal
                })
        
        return jsonify({"response_action": "clear"})

    # Handle metric submission
    elif payload.get("type") == "view_submission" and \
         payload.get("view", {}).get("callback_id") == "log_metrics_modal":

        category_id = int(payload["view"]["private_metadata"])
        state_values = payload["view"]["state"]["values"]
        
        # Get metric date
        metric_date = state_values["metric_date"]["date_selection"]["selected_date"]
        
        # Get notes
        notes = None
        if "notes" in state_values and state_values["notes"]["notes_input"]["value"]:
            notes = state_values["notes"]["notes_input"]["value"]
        
        # Get category details
        category_data = get_category_with_metrics(category_id)
        
        # Extract metric values
        metric_values = []
        metric_entries_for_csv = []
        
        for metric_def in category_data['metrics']:
            block_id = f"metric_{metric_def['id']}"
            action_id = f"value_{metric_def['id']}"
            
            if block_id in state_values and state_values[block_id][action_id]["value"]:
                try:
                    value = float(state_values[block_id][action_id]["value"])
                    metric_values.append({
                        'metric_definition_id': metric_def['id'],
                        'value': value
                    })
                    metric_entries_for_csv.append({
                        'metric_name': metric_def['name'],
                        'value': value,
                        'units': metric_def['units']
                    })
                except ValueError:
                    print(f"Invalid value for {metric_def['name']}", file=sys.stderr)
        
        if metric_values:
            # Log to database
            logged_ids = log_metrics(category_id, user_id, metric_date, metric_values, notes)
            
            # Also log to CSV for compatibility
            append_metric_rows(
                category_data['name'], 
                user_id, 
                metric_date, 
                metric_entries_for_csv, 
                notes
            )
            
            print(f"Logged {len(logged_ids)} metrics for category {category_data['name']}", file=sys.stderr)

        return jsonify({"response_action": "clear"})

    return "", 200


if __name__ == "__main__":
    app.run(port=3000, debug=True)