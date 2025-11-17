from flask import Flask, request, jsonify
import os, requests, sys, json, csv
from pathlib import Path
from datetime import datetime, timezone

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

CSV_PATH = Path("data/metrics.csv")

def append_metric_row(user_id: str, metric_name: str, metric_value: str):
    new_file = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp_utc", "user_id", "metric_name", "metric_value"])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            user_id,
            metric_name,
            metric_value,
        ])


@app.post("/slack/commands")
def handle_slash_command():
    trigger_id = request.form.get("trigger_id")

    resp = requests.post(
        "https://slack.com/api/views.open",
        headers={
            "Authorization": f"Bearer {BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "trigger_id": trigger_id,
            "view": {
                "type": "modal",
                "callback_id": "track_metric_modal",
                "title": {"type": "plain_text", "text": "Track a Metric"},
                "submit": {"type": "plain_text", "text": "Save"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "metric_name_b",
                        "label": {"type": "plain_text", "text": "Metric name"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "metric_name"
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "metric_value_b",
                        "label": {"type": "plain_text", "text": "Value"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "metric_value"
                        },
                    },
                ],
            },
        },
    )

    print("views.open status:", resp.status_code, file=sys.stderr)
    print("views.open body:", resp.text, file=sys.stderr)

    return jsonify(response_type="ephemeral", text="Opening modal…")


@app.post("/slack/interactions")
def handle_interactions():
    payload_raw = request.form.get("payload")
    if not payload_raw:
        return "", 200

    payload = json.loads(payload_raw)

    if payload.get("type") == "view_submission" and \
       payload.get("view", {}).get("callback_id") == "track_metric_modal":

        user_id = payload.get("user", {}).get("id", "unknown")

        state_values = payload["view"]["state"]["values"]
        metric_name = state_values["metric_name_b"]["metric_name"]["value"]
        metric_value = state_values["metric_value_b"]["metric_value"]["value"]

        append_metric_row(user_id, metric_name, metric_value)
        print(f"Saved metric: {metric_name}={metric_value} from {user_id}", file=sys.stderr)

        return jsonify({"response_action": "clear"})

    return "", 200


if __name__ == "__main__":
    app.run(port=3000, debug=True)