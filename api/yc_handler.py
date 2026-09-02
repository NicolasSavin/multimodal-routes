from app import app
import base64


def handler(event, context):
    method = event.get("httpMethod") or "GET"
    params = dict(event.get("queryStringParameters") or {})
    path = params.pop("path", None) or event.get("path") or "/"
    if path in ("/", "", None):
        path = "/health"
    if not str(path).startswith("/"):
        path = "/" + path
    query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None and k != "path")
    url = path + (("?" + query) if query else "")
    headers = event.get("headers") or {}
    headers_l = {str(k).lower(): v for k, v in headers.items()}
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": "",
        }
    body = event.get("body") or ""
    if event.get("isBase64Encoded") and body:
        try:
            body = base64.b64decode(body).decode("utf-8", "replace")
        except Exception:
            body = ""
    client = app.test_client()
    resp = client.open(
        url,
        method=method,
        data=body or None,
        content_type=headers_l.get("content-type") or "application/json",
    )
    return {
        "statusCode": resp.status_code,
        "headers": {
            "Content-Type": resp.content_type or "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": resp.get_data(as_text=True),
        "isBase64Encoded": False,
    }
