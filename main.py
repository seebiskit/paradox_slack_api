from flask import Flask, request, jsonify
import os, requests, sys, json, csv
from pathlib import Path
from datetime import datetime, timezone, date
from database import (
    init_database, get_category_templates, get_user_categories, 
    get_category_with_metrics, create_category_from_template, log_metrics, create_custom_category
)
from category_templates import setup_default_templates
from google_sheets_sync import sync_metrics_to_sheets

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
            "text": {"type": "plain_text", "text": category['name']},
            "value": f"category_{category['id']}"
        })
    
    # Sort all options alphabetically by display text
    options.sort(key=lambda x: x["text"]["text"])
    
    # Add "Create New Category" as the last option in dropdown
    options.append({
        "text": {"type": "plain_text", "text": "Create New Category..."},
        "value": "create_new_category"
    })
    
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
    
    return {
        "type": "modal",
        "callback_id": "select_category_modal",
        "title": {"type": "plain_text", "text": "Log Metrics"},
        "blocks": blocks,
        "submit": {"type": "plain_text", "text": "Next"}
    }

def build_create_category_modal():
    """Build the create category modal for custom categories"""
    return {
        "type": "modal",
        "callback_id": "create_category_modal",
        "title": {"type": "plain_text", "text": "Create Category"},
        "blocks": [
            {
                "type": "input",
                "block_id": "category_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., Special Event Attendance"}
                },
                "label": {"type": "plain_text", "text": "Category Name"}
            }
        ],
        "submit": {"type": "plain_text", "text": "Next: Add Metrics"}
    }

def build_add_metrics_modal(category_name, category_icon):
    """Build the modal for adding metrics to a new category"""
    return {
        "type": "modal",
        "callback_id": "add_metrics_modal",
        "title": {"type": "plain_text", "text": "Add Metrics"},
        "private_metadata": json.dumps({"name": category_name, "icon": category_icon}),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Category:* {category_icon} {category_name}\n\nAdd the metrics you want to track:"
                }
            },
            {
                "type": "input",
                "block_id": "metric1_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., Adults, Revenue, Duration"}
                },
                "label": {"type": "plain_text", "text": "Metric 1 Name"}
            },
            {
                "type": "input",
                "block_id": "metric1_units",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "units_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., people, dollars, minutes"}
                },
                "label": {"type": "plain_text", "text": "Metric 1 Units"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric1_optional",
                "element": {
                    "type": "checkboxes",
                    "action_id": "optional_input",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Make this metric optional"},
                            "value": "optional"
                        }
                    ]
                },
                "label": {"type": "plain_text", "text": "Metric 1 Settings"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric2_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., Children, Transactions"}
                },
                "label": {"type": "plain_text", "text": "Metric 2 Name"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric2_units",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "units_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., people, count"}
                },
                "label": {"type": "plain_text", "text": "Metric 2 Units"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric2_optional",
                "element": {
                    "type": "checkboxes",
                    "action_id": "optional_input",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Make this metric optional"},
                            "value": "optional"
                        }
                    ]
                },
                "label": {"type": "plain_text", "text": "Metric 2 Settings"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric3_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "Add another metric (optional)"}
                },
                "label": {"type": "plain_text", "text": "Metric 3 Name"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric3_units",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "units_input",
                    "placeholder": {"type": "plain_text", "text": "Units for metric 3"}
                },
                "label": {"type": "plain_text", "text": "Metric 3 Units"},
                "optional": True
            },
            {
                "type": "input",
                "block_id": "metric3_optional",
                "element": {
                    "type": "checkboxes",
                    "action_id": "optional_input",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Make this metric optional"},
                            "value": "optional"
                        }
                    ]
                },
                "label": {"type": "plain_text", "text": "Metric 3 Settings"},
                "optional": True
            }
        ],
        "submit": {"type": "plain_text", "text": "Create Category"}
    }

@app.post("/slack/commands")
def handle_slash_command():
    trigger_id = request.form.get("trigger_id")
    user_id = request.form.get("user_id")
    channel_id = request.form.get("channel_id")
    
    print(f"Slash command - Channel ID: {channel_id}", file=sys.stderr)
    
    # don't think I need to send user_id back now that I'm not create any custom categories for just one user
    # will need to add back if we want to ever control access to certain datapoints (i.e., giving)
    modal = build_category_selection_modal(user_id)
    
    # Store channel ID in modal metadata for later use
    modal["private_metadata"] = json.dumps({"channel_id": channel_id})

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
    
    # Post to Slack checkbox (default checked)
    blocks.append({
        "type": "input",
        "block_id": "post_to_slack",
        "optional": True,
        "element": {
            "type": "checkboxes",
            "action_id": "post_checkbox",
            "initial_options": [
                {
                    "text": {"type": "plain_text", "text": "Post metric to Slack"},
                    "value": "post_to_slack"
                }
            ],
            "options": [
                {
                    "text": {"type": "plain_text", "text": "Post metric to Slack"},
                    "value": "post_to_slack"
                }
            ]
        },
        "label": {"type": "plain_text", "text": "📢 Share Results"}
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
    # is the best design a big if statement for interactions
    # Handle block actions (if any needed in future)
    if payload.get("type") == "block_actions":
        print(f"Block action received: {json.dumps(payload, indent=2)}", file=sys.stderr)
        action = payload["actions"][0]
        print(f"Action ID: {action.get('action_id')}", file=sys.stderr)
        # No button handlers needed anymore - everything is handled via dropdown
        return "", 200

    # Handle create category form submission (step 1 - name and icon)
    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "create_category_modal":
        
        state_values = payload["view"]["state"]["values"]
        
        # Get category name and set default icon
        category_name = state_values["category_name"]["name_input"]["value"].strip()
        category_icon = "📊"  # default icon
        
        # Show the add metrics modal
        add_metrics_modal = build_add_metrics_modal(category_name, category_icon)
        return jsonify({
            "response_action": "update",
            "view": add_metrics_modal
        })

    # Handle add metrics form submission (step 2 - define metrics)
    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "add_metrics_modal":
        
        # Get category info from private metadata
        category_info = json.loads(payload["view"]["private_metadata"])
        category_name = category_info["name"]
        category_icon = category_info["icon"]
        
        state_values = payload["view"]["state"]["values"]
        
        # Extract metrics
        metrics = []
        for i in range(1, 4):  # metrics 1, 2, 3
            name_key = f"metric{i}_name"
            units_key = f"metric{i}_units"
            optional_key = f"metric{i}_optional"
            
            if name_key in state_values and state_values[name_key]["name_input"]["value"]:
                metric_name = state_values[name_key]["name_input"]["value"].strip()
                metric_units = ""
                if units_key in state_values and state_values[units_key]["units_input"]["value"]:
                    metric_units = state_values[units_key]["units_input"]["value"].strip()
                
                # Check if metric is marked as optional
                is_optional = False
                if optional_key in state_values and state_values[optional_key]["optional_input"]["selected_options"]:
                    is_optional = True
                
                metrics.append({
                    "name": metric_name,
                    "units": metric_units or None,
                    "is_required": not is_optional
                })
        
        if not metrics:
            return jsonify({
                "response_action": "errors",
                "errors": {
                    "metric1_name": "At least one metric is required."
                }
            })
        
        # Create the custom category
        try:
            category_id = create_custom_category(category_name, category_icon, user_id, metrics)
            print(f"Created custom category {category_id} for user {user_id}", file=sys.stderr)
            
            # After creating category, redirect to metric entry modal
            category_data = get_category_with_metrics(category_id)
            if category_data:
                metric_modal = build_metric_entry_modal(
                    category_id, 
                    category_data['name'], 
                    category_data['metrics']
                )
                
                # Need to get channel ID - since we're in custom category flow, we need to trace it back
                # For now, we'll have to send as DM since we can't easily get the original channel ID
                metric_modal["private_metadata"] = json.dumps({
                    "category_id": category_id,
                    "channel_id": None  # Will fall back to DM
                })
                
                return jsonify({
                    "response_action": "update",
                    "view": metric_modal
                })
        except Exception as e:
            error_msg = str(e).lower()
            print(f"Error creating custom category: {e}", file=sys.stderr)
            
            # Check if it's a duplicate name error
            if "unique constraint" in error_msg or "already exists" in error_msg:
                return jsonify({
                    "response_action": "errors",
                    "errors": {
                        "category_name": "A category with that name already exists. Please log your metric under the existing category or pick a different name."
                    }
                })
            else:
                return jsonify({
                    "response_action": "errors",
                    "errors": {
                        "category_name": "Failed to create category. Please try again."
                    }
                })

    # Handle category selection
    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "select_category_modal":

        # Get channel ID from metadata
        channel_info = json.loads(payload["view"].get("private_metadata", "{}"))
        channel_id = channel_info.get("channel_id")
        print(f"Category selection - Channel ID from metadata: {channel_id}", file=sys.stderr)

        state_values = payload["view"]["state"]["values"]
        selection = state_values["category_select"]["category_selection"]["selected_option"]["value"]
        
        print(f"Category selection: {selection}", file=sys.stderr)
        
        category_id = None
        
        # Handle different selection types
        if selection.startswith("category_"):
            category_id = int(selection.split("_")[1])
        elif selection == "create_new_category":
            # Show create category modal
            create_modal = build_create_category_modal()
            return jsonify({
                "response_action": "update",
                "view": create_modal
            })
        
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
                
                # Pass channel ID to metric modal
                metric_modal["private_metadata"] = json.dumps({
                    "category_id": category_id,
                    "channel_id": channel_id
                })
                
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

        # Get metadata (category_id and channel_id)
        try:
            metadata_str = payload["view"]["private_metadata"]
            if metadata_str:
                metadata = json.loads(metadata_str)
                category_id = metadata.get("category_id")
                channel_id = metadata.get("channel_id")
            else:
                # Handle case where private_metadata is empty (custom category creation flow)
                print("No metadata found, extracting from payload", file=sys.stderr)
                category_id = None  # Will be determined from URL or other means
                channel_id = None
                metadata = {}
        except json.JSONDecodeError:
            print("Error parsing metadata JSON", file=sys.stderr)
            category_id = None
            channel_id = None
            metadata = {}
        
        print(f"Metric submission - Channel ID from metadata: {channel_id}", file=sys.stderr)
        print(f"Full metadata: {metadata}", file=sys.stderr)
        
        state_values = payload["view"]["state"]["values"]
        
        # Get metric date
        metric_date = state_values["metric_date"]["date_selection"]["selected_date"]
        
        # Get notes
        notes = None
        if "notes" in state_values and state_values["notes"]["notes_input"]["value"]:
            notes = state_values["notes"]["notes_input"]["value"]
        
        # Check if should post to Slack
        should_post_to_slack = False
        if "post_to_slack" in state_values and state_values["post_to_slack"]["post_checkbox"]["selected_options"]:
            should_post_to_slack = True
        
        # Get category details
        category_data = get_category_with_metrics(category_id)
        
        # Extract metric values
        metric_values = []
        metric_entries_for_csv = []
        metric_display_list = []
        
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
                    
                    # Format for display
                    units_display = f" {metric_def['units']}" if metric_def['units'] else ""
                    # Format number nicely (remove .0 for whole numbers)
                    formatted_value = int(value) if value == int(value) else value
                    metric_display_list.append(f"• {metric_def['name']}: {formatted_value}{units_display}")
                    
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
            
            # Get user display name for Google Sheets (we'll get it again for Slack later if needed)
            user_display_name = "Unknown User"
            try:
                user_info_resp = requests.get(
                    "https://slack.com/api/users.info",
                    headers={"Authorization": f"Bearer {BOT_TOKEN}"},
                    params={"user": user_id}
                )
                if user_info_resp.status_code == 200:
                    user_data = user_info_resp.json()
                    if user_data.get("ok"):
                        profile = user_data.get("user", {}).get("profile", {})
                        user_display_name = (
                            profile.get("display_name") or 
                            profile.get("real_name") or 
                            user_data.get("user", {}).get("real_name") or 
                            user_data.get("user", {}).get("name", "Unknown User")
                        )
            except Exception as e:
                print(f"Error getting user info for Google Sheets: {e}", file=sys.stderr)
            
            # Sync to Google Sheets in real-time
            try:
                sheets_success = sync_metrics_to_sheets(
                    category_name=category_data['name'],
                    metric_entries=metric_entries_for_csv,
                    metric_date=metric_date,
                    user_display_name=user_display_name,
                    notes=notes
                )
                if sheets_success:
                    print("✅ Synced metrics to Google Sheets", file=sys.stderr)
                else:
                    print("⚠️ Google Sheets sync failed (check configuration)", file=sys.stderr)
            except Exception as e:
                print(f"❌ Error syncing to Google Sheets: {e}", file=sys.stderr)
            
            # Post to Slack if requested
            if should_post_to_slack and metric_display_list:
                # Don't overwrite the channel_id variable!
                print(f"About to post - channel_id is: {channel_id}", file=sys.stderr)
                
                # Get user display name
                user_display_name = "Someone"
                try:
                    user_info_resp = requests.get(
                        "https://slack.com/api/users.info",
                        headers={"Authorization": f"Bearer {BOT_TOKEN}"},
                        params={"user": user_id}
                    )
                    print(f"User info response: {user_info_resp.status_code} - {user_info_resp.text}", file=sys.stderr)
                    if user_info_resp.status_code == 200:
                        user_data = user_info_resp.json()
                        if user_data.get("ok"):
                            profile = user_data.get("user", {}).get("profile", {})
                            user_display_name = (
                                profile.get("display_name") or 
                                profile.get("real_name") or 
                                user_data.get("user", {}).get("real_name") or 
                                user_data.get("user", {}).get("name", "Someone")
                            )
                            print(f"Found user display name: {user_display_name}", file=sys.stderr)
                        else:
                            print(f"Slack API error: {user_data.get('error')}", file=sys.stderr)
                except Exception as e:
                    print(f"Error getting user info: {e}", file=sys.stderr)

                # Build message
                message_lines = [
                    f"📊 *{user_display_name} logged a metric*",
                    f"*{category_data['name']}* ({metric_date})",
                    "",
                    "\n".join(metric_display_list)
                ]
                
                if notes:
                    message_lines.extend(["", f"> {notes}"])
                
                message_text = "\n".join(message_lines)
                
                # Get channel ID from original slash command context if available
                original_channel = request.form.get("channel_id") if hasattr(request, 'form') else None
                
                # Post message to Slack
                try:
                    resp = requests.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            "Authorization": f"Bearer {BOT_TOKEN}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "channel": channel_id or payload.get("user", {}).get("id"),  # Post to original channel or DM
                            "text": message_text,
                            "unfurl_links": False
                        }
                    )
                    response_data = resp.json()
                    actual_channel_used = channel_id or payload.get("user", {}).get("id")
                    print(f"Posted to Slack: {resp.status_code}", file=sys.stderr)
                    print(f"Slack response: {resp.text}", file=sys.stderr)
                    
                    # If bot not in channel, try sending DM instead
                    if not response_data.get("ok") and response_data.get("error") == "not_in_channel":
                        user_id_for_dm = payload.get("user", {}).get("id")
                        print(f"Bot not in channel, sending DM to user {user_id_for_dm}", file=sys.stderr)
                        
                        dm_resp = requests.post(
                            "https://slack.com/api/chat.postMessage",
                            headers={
                                "Authorization": f"Bearer {BOT_TOKEN}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "channel": user_id_for_dm,
                                "text": f"📊 *Metrics logged!* (Bot not in channel, so sending you a DM)\n\n{message_text}",
                                "unfurl_links": False
                            }
                        )
                        print(f"DM sent: {dm_resp.status_code} - {dm_resp.text}", file=sys.stderr)
                except Exception as e:
                    print(f"Error posting to Slack: {e}", file=sys.stderr)

        return jsonify({"response_action": "clear"})

    return "", 200


if __name__ == "__main__":
    app.run(port=3000, debug=True)