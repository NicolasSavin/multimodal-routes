from app import app


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
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": "",
        }
    client = app.test_client()
    resp = client.open(url, method=method)
    return {
        "statusCode": resp.status_code,
        "headers": {
            "Content-Type": resp.content_type or "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": resp.get_data(as_text=True),
        "isBase64Encoded": False,
    }
