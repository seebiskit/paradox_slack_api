"""
Slack request signature verification for security.

Implements HMAC SHA256 verification according to Slack's documentation:
https://api.slack.com/authentication/verifying-requests-from-slack
"""

import os
import hmac
import hashlib
import time
from functools import wraps
from flask import request, jsonify
import sys


SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")


def verify_slack_signature(signing_secret: str, timestamp: str, body: str, signature: str) -> bool:
    """
    Verify Slack request signature using HMAC SHA256.

    Args:
        signing_secret: Your app's signing secret from Slack
        timestamp: X-Slack-Request-Timestamp header value
        body: Raw request body as string
        signature: X-Slack-Signature header value (format: v0=hash)

    Returns:
        True if signature is valid, False otherwise
    """
    # Check if timestamp is within 5 minutes (replay attack protection)
    try:
        request_timestamp = int(timestamp)
        current_timestamp = int(time.time())

        if abs(current_timestamp - request_timestamp) > 60 * 5:
            print(f"Request timestamp too old: {abs(current_timestamp - request_timestamp)}s difference", file=sys.stderr)
            return False
    except (ValueError, TypeError):
        print(f"Invalid timestamp format: {timestamp}", file=sys.stderr)
        return False

    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{body}"

    # Calculate expected signature
    expected_signature = 'v0=' + hmac.new(
        signing_secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


def require_slack_verification(f):
    """
    Flask decorator to verify Slack request signatures.

    Apply this to all Slack webhook endpoints for security.
    Returns 401 Unauthorized if verification fails.

    Usage:
        @app.post("/slack/commands")
        @require_slack_verification
        def handle_slash_command():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip verification if signing secret is not configured (local dev)
        if not SLACK_SIGNING_SECRET:
            print("WARNING: SLACK_SIGNING_SECRET not set - skipping signature verification", file=sys.stderr)
            return f(*args, **kwargs)

        # Get required headers
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')

        if not timestamp or not signature:
            print("Missing required headers: X-Slack-Request-Timestamp or X-Slack-Signature", file=sys.stderr)
            return jsonify({"error": "Unauthorized"}), 401

        # Get raw request body
        body = request.get_data(as_text=True)

        # Verify signature
        if not verify_slack_signature(SLACK_SIGNING_SECRET, timestamp, body, signature):
            print(f"Slack signature verification failed for {request.path}", file=sys.stderr)
            print(f"Timestamp: {timestamp}, Signature: {signature[:20]}...", file=sys.stderr)
            return jsonify({"error": "Unauthorized"}), 401

        # Verification passed
        return f(*args, **kwargs)

    return decorated_function


def get_signing_secret_status() -> dict:
    """
    Check if signing secret is configured.
    Useful for startup checks.

    Returns:
        dict with status information
    """
    return {
        "configured": bool(SLACK_SIGNING_SECRET),
        "length": len(SLACK_SIGNING_SECRET) if SLACK_SIGNING_SECRET else 0
    }
