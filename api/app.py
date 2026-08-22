import os
import time

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

YC = "https://bba1p30liradr6hj8olf.containers.yandexcloud.net"
YKEY = os.environ.get("YANDEX_RASP_KEY") or os.environ.get("YANDEX_RASP_API_KEY") or ""


def yandex_code(q):
    d = requests.get(
        "https://suggests.rasp.yandex.net/all_suggests",
        params={"format": "old", "part": q},
        timeout=8,
    ).json()
    for row in (d or [None, []])[1]:
        if row and str(row[0]).startswith(("c", "s")):
            return row[0], row[1]
    return None, q


def yandex_search(fr, to, date):
    if not YKEY:
        return [], "no_key"
    a, an = yandex_code(fr)
    b, bn = yandex_code(to)
    if not a or not b:
        return [], "no_codes"
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
        },
        timeout=12,
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
                "from": (s.get("from") or {}).get("title") or an,
                "to": (s.get("to") or {}).get("title") or bn,
                "type": th.get("transport_type") or "train",
                "has_transfers": bool(s.get("has_transfers")),
                "segments": [
                    {
                        "number": th.get("number"),
                        "transport_type": th.get("transport_type") or "train",
                        "origin": (s.get("from") or {}).get("title"),
                        "destination": (s.get("to") or {}).get("title"),
                        "departure_time": s.get("departure"),
                        "arrival_time": s.get("arrival"),
                    }
                ],
            }
        )
    return out, data.get("error") or "ok"


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY)})


@app.get("/trains")
def trains():
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    date = (request.args.get("date") or "").strip()
    if not origin or not dest or not date:
        return jsonify({"error": "from, to, date"}), 400
    err = None
    try:
        trains_out, status = yandex_search(origin, dest, date)
        return jsonify(
            {
                "source": "yandex-rasp",
                "from": origin,
                "to": dest,
                "trains": trains_out,
                "yandex_configured": bool(YKEY),
                "status": status,
            }
        )
    except Exception as e:
        err = str(e)
        trains_out = []
    try:
        r = requests.post(
            YC + "/api/v1/routes/search",
            json={
                "origin": origin,
                "destination": dest,
                "departure_date": date,
                "passengers": 1,
                "allowed_transport": ["train", "bus"],
                "max_transfers": 1,
            },
            timeout=25,
        )
        data = r.json()
        routes = data.get("routes") or data.get("partially_confirmed_routes") or []
        for rt in routes:
            segs = rt.get("segments") or []
            first = segs[0] if segs else {}
            last = segs[-1] if segs else {}
            trains_out.append(
                {
                    "number": first.get("number"),
                    "dep": first.get("departure_time"),
                    "arr": last.get("arrival_time"),
                    "from": first.get("origin") or origin,
                    "to": last.get("destination") or dest,
                    "type": first.get("transport_type") or "train",
                    "has_transfers": bool(rt.get("transfers_count")),
                    "transfer_city": rt.get("transfer_city"),
                    "segments": segs,
                }
            )
        return jsonify(
            {
                "source": "yandex-cloud-fallback",
                "from": origin,
                "to": dest,
                "trains": trains_out,
                "yandex_configured": bool(YKEY),
                "error": err,
            }
        )
    except Exception as e2:
        return jsonify({"source": "error", "trains": [], "error": err or str(e2), "yandex_configured": bool(YKEY)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
