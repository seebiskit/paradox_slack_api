# Paradox form list demo
## Get Started
1. Create python venv `python -m venv .venv`
2. Activate the venv `source .venv/bin/activate`
3. Install pip packages `pip install -r requirements.txt`
4. Start the Flask API `python main.py`

## From ChatGPT on how to setup.

# 🚀 1. Create a Slack App

1. Visit **[https://api.slack.com/apps](https://api.slack.com/apps)**
2. Click **Create New App → From scratch**
3. Give it a name (e.g., “Metric Logger”)
4. Select the Slack workspace where you want this installed

---

# 🔐 2. Configure OAuth & Permissions

Inside your Slack app:

### **Bot Token Scopes**

Navigate to:

**OAuth & Permissions → Scopes → Bot Token Scopes**

Add the following scope:

* `commands`

(This scope is required to open modals.)

### **Install the App**

Still under **OAuth & Permissions**, scroll up and click:

**Install App to Workspace → Allow**

You will now see your:

### ✔ Bot User OAuth Token (`xoxb-...`)

Copy this value — you will set it as `SLACK_BOT_TOKEN`.

> If Slack only shows `xoxe-...` refresh tokens and **no** `xoxb-...` bot token, token rotation is enabled.
> Either disable rotation (recommended for development) or exchange the refresh token using the OAuth refresh flow.

---

# 💬 3. Create the Slash Command

Go to **Slash Commands → Create New Command**:

| Field       | Value               |
| ----------- | ------------------- |
| Command     | `/track_metric`     |
| Description | Log a metric        |
| Usage Hint  | `[metric]`          |
| Request URL | leave blank for now |

Click **Save**.
You will return later to fill in the Request URL once ngrok is running.

---

# ⚙️ 4. Enable Interactivity

Slack sends modal submissions to a separate endpoint.

1. Go to **Interactivity & Shortcuts**
2. Toggle **Interactivity: ON**
3. For now, set the Request URL to a placeholder (you will update it soon)
4. Save changes

Slack will reject modal submissions unless this is turned on.

---

# 🔧 5. Set Your Slack Bot Token

Wherever you run the backend, set the environment variable:

```bash
export SLACK_BOT_TOKEN="xoxb-XXXXXXXX"
```

Your backend uses this token to call Slack’s `views.open` API, which opens the modal.

---

# 🌐 6. Expose the Backend with ngrok (Development Only)

Slack must be able to reach your `/slack/commands` and `/slack/interactions` routes from the public internet.

If using ngrok:

```bash
ngrok http 3000
```

You will see an HTTPS URL, for example:

```
https://abc123.ngrok-free.dev
```

Copy this value — you will plug it into Slack next.

---

# 🔗 7. Connect Slack to Your Backend

Update the Slack app to send requests to your backend.

### **A. Slash Command URL**

Go to:

**Slash Commands → /track_metric → Edit**

Set:

```
https://<ngrok-domain>/slack/commands
```

Save.

### **B. Interactivity URL**

Go to:

**Interactivity & Shortcuts**

Set:

```
https://<ngrok-domain>/slack/interactions
```

Save.

Slack will automatically test the URLs.

---

# 🧪 8. Test the Integration

1. In your Slack workspace, type:

```
/track_metric
```

2. A modal should appear.
3. Fill it out and hit **Save**.
4. Submissions will be sent to `/slack/interactions`, and the backend will process/store the data.

---

# 🎉 Setup Complete

Slack is now connected to your backend.
The `/track_metric` slash command will open the modal and save submissions according to your server’s logic.

---

If you want, I can also generate:

* A **“Troubleshooting”** section
* A **diagram** of the Slack → backend request flow
* A **production deployment guide** (AWS Lambda, API Gateway, DynamoDB)
