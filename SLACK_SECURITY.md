# Slack Request Signature Verification

This app implements Slack's request signature verification to ensure all inbound requests are genuinely from Slack and not from malicious actors.

## Security Features

1. **HMAC SHA256 Signature Verification** - Verifies each request using your app's signing secret
2. **Replay Attack Protection** - Rejects requests older than 5 minutes
3. **Constant-Time Comparison** - Prevents timing attacks
4. **Comprehensive Logging** - Logs all failed verification attempts

## Setup

### 1. Get Your Signing Secret

1. Go to https://api.slack.com/apps
2. Select your app
3. Navigate to **Settings > Basic Information**
4. Scroll to **App Credentials**
5. Copy your **Signing Secret**

### 2. Configure Environment Variable

Add to your `.env` file:

```bash
SLACK_SIGNING_SECRET=your_actual_signing_secret_here
```

**On your server**, set this environment variable:

```bash
export SLACK_SIGNING_SECRET=your_actual_signing_secret_here
```

Or add it to your Docker Compose / deployment configuration.

### 3. Verify Configuration

When the app starts, you'll see one of these messages:

```
✓ Slack signing secret configured (32 chars)
```

Or if not configured:

```
⚠️  WARNING: Slack signing secret NOT configured - signature verification disabled!
```

## How It Works

Every request from Slack includes these headers:

- `X-Slack-Request-Timestamp` - Unix timestamp when request was sent
- `X-Slack-Signature` - HMAC SHA256 hash for verification

The verification process:

1. **Check timestamp** - Reject if older than 5 minutes (replay protection)
2. **Create base string** - Concatenate `v0:{timestamp}:{body}`
3. **Calculate HMAC** - Use signing secret to hash the base string
4. **Compare signatures** - Use constant-time comparison for security

If verification fails, the request is rejected with `401 Unauthorized`.

## Protected Endpoints

These endpoints are protected with signature verification:

- `POST /slack/commands` - Slash commands
- `POST /slack/interactions` - Interactive components (modals, buttons, etc.)

## Local Development

During local development with ngrok or similar tunnels, you can:

1. **Use the signing secret** (recommended) - Set `SLACK_SIGNING_SECRET` in `.env`
2. **Skip verification** - Leave `SLACK_SIGNING_SECRET` empty (NOT recommended for production)

**⚠️ NEVER deploy to production without setting the signing secret!**

## Troubleshooting

### Requests getting 401 Unauthorized

Check the logs for one of these errors:

**Missing headers:**
```
Missing required headers: X-Slack-Request-Timestamp or X-Slack-Signature
```
→ Your Slack app configuration may be incorrect

**Timestamp too old:**
```
Request timestamp too old: 310s difference
```
→ Check your server's clock synchronization (NTP)

**Signature mismatch:**
```
Slack signature verification failed for /slack/commands
```
→ Verify you're using the correct signing secret

### Finding Your Signing Secret

1. Go to https://api.slack.com/apps → Your App
2. Settings > Basic Information
3. App Credentials section
4. Copy the **Signing Secret** (NOT the Client Secret)

## Security Best Practices

✓ **Always enable verification in production**
✓ **Keep your signing secret secure** (never commit to git)
✓ **Rotate signing secret if compromised**
✓ **Monitor logs for failed verification attempts**
✓ **Use environment variables for secrets**

## References

- [Slack Documentation: Verifying requests from Slack](https://api.slack.com/authentication/verifying-requests-from-slack)
- [OWASP: HMAC Authentication](https://owasp.org/www-community/controls/HMAC_Authentication)
