import os
import time

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

RZD = "https://ticket.rzd.ru"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ticket.rzd.ru/",
    "Origin": "https://ticket.rzd.ru",
}
YKEY = os.environ.get("YANDEX_RASP_KEY") or os.environ.get("YANDEX_RASP_API_KEY") or ""
RZD_TIMEOUT = 6


def rzd_get(path, params=None, timeout=RZD_TIMEOUT):
    r = requests.get(RZD + path, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    if not r.content:
        return {}
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:500]}


def rzd_post(path, json_body, params=None, timeout=RZD_TIMEOUT):
    r = requests.post(RZD + path, params=params, json=json_body, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY)})


@app.get("/suggest")
def suggest():
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify([])
    try:
        sug = requests.get(
            "https://suggests.rasp.yandex.net/all_suggests",
            params={"format": "old", "part": q},
            timeout=10,
        ).json()
        out = []
        for row in (sug or [None, []])[1][:20]:
            if row:
                out.append({"code": row[0], "name": row[1], "region": row[2] if len(row) > 2 else ""})
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.get("/trains")
def trains():
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    date = (request.args.get("date") or "").strip()
    if not origin or not dest or not date:
        return jsonify({"error": "from, to, date обязательны"}), 400
    y = yandex_search(origin, dest, date)
    rzd_err = None
    try:
        data = rzd_get(
            "/isdk/suggests",
            {"Query": origin, "TransportType": "rail", "GroupResults": "true", "Language": "ru"},
        )
        if data:
            rzd_err = None
    except Exception as e:
        rzd_err = str(e)
    return jsonify(
        {
            "source": "yandex" if y else "none",
            "from": origin,
            "to": dest,
            "trains": y,
            "error_rzd": rzd_err,
            "yandex_configured": bool(YKEY),
        }
    )


@app.post("/cars")
def cars():
    return jsonify({"error": "ticket.rzd.ru недоступен с Render US", "cars": []}), 503


def yandex_search(fr, to, date):
    if not YKEY:
        return []
    try:
        sug = requests.get("https://suggests.rasp.yandex.net/all_suggests", params={"format": "old", "part": fr}, timeout=12).json()
        to_sug = requests.get("https://suggests.rasp.yandex.net/all_suggests", params={"format": "old", "part": to}, timeout=12).json()

        def code(block):
            rows = (block or [None, []])[1]
            for row in rows:
                if row and str(row[0]).startswith(("c", "s")):
                    return row[0]
            return None

        a, b = code(sug), code(to_sug)
        if not a or not b:
            return []
        data = requests.get(
            "https://api.rasp.yandex.net/v3.0/search/",
            params={
                "apikey": YKEY,
                "from": a,
                "to": b,
                "date": date,
                "lang": "ru_RU",
                "limit": 20,
                "transport_types": "train,bus",
                "transfers": 1,
            },
            timeout=20,
        ).json()
        out = []
        for s in data.get("segments") or []:
            th = s.get("thread") or {}
            out.append(
                {
                    "number": th.get("number"),
                    "name": th.get("title"),
                    "dep": s.get("departure"),
                    "arr": s.get("arrival"),
                    "from": (s.get("from") or {}).get("title"),
                    "to": (s.get("to") or {}).get("title"),
                    "type": th.get("transport_type"),
                    "has_transfers": s.get("has_transfers"),
                    "groups": [],
                }
            )
        return out
    except Exception:
        return []


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
