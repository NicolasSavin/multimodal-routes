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


def rzd_seats(fr, to, date, pax):
    r = requests.get(
        YC + "/api/v1/seats/rzd",
        params={"origin": fr, "destination": to, "date": date, "passengers": pax},
        timeout=35,
    )
    return r.json()


def _norm(n):
    return "".join(ch for ch in str(n or "").upper() if ch.isalnum())


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY)})


@app.get("/trains")
def trains():
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    date = (request.args.get("date") or "").strip()
    pax = int(request.args.get("adults") or request.args.get("pax") or 1)
    if not origin or not dest or not date:
        return jsonify({"error": "from, to, date"}), 400
    err = None
    trains_out, status = [], None
    try:
        trains_out, status = yandex_search(origin, dest, date)
    except Exception as e:
        err = str(e)
    seats = {}
    seats_err = None
    try:
        raw = rzd_seats(origin, dest, date, pax)
        if not raw.get("ok"):
            seats_err = raw.get("error") or raw.get("error_type")
        for t in raw.get("trains") or []:
            seats[_norm(t.get("number"))] = t
    except Exception as e:
        seats_err = str(e)
    for item in trains_out:
        hit = seats.get(_norm(item.get("number")))
        if hit:
            item["rzd"] = hit
    return jsonify(
        {
            "source": "yandex-rasp+rzd" if trains_out else "error",
            "from": origin,
            "to": dest,
            "trains": trains_out,
            "yandex_configured": bool(YKEY),
            "status": status,
            "error": err,
            "rzd_error": seats_err,
            "rzd_trains": len(seats),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
