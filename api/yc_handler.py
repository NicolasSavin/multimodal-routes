from app import app


def handler(event, context):
    method = event.get("httpMethod") or "GET"
    path = event.get("path") or event.get("url") or "/"
    if not path.startswith("/"):
        path = "/" + path
    params = event.get("queryStringParameters") or {}
    query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = path + (("?" + query) if query else "")

    headers = {}
    raw = event.get("headers") or {}
    for key, val in raw.items():
        if key.lower() not in {"host", "content-length"}:
            headers[key] = val

    body = event.get("body") or ""
    if event.get("isBase64Encoded") and body:
        import base64

        body = base64.b64decode(body)

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
            "body": "",
        }

    client = app.test_client()
    resp = client.open(url, method=method, data=body or None, headers=headers)
    return {
        "statusCode": resp.status_code,
        "headers": {
            "Content-Type": resp.content_type or "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": resp.get_data(as_text=True),
        "isBase64Encoded": False,
    }
