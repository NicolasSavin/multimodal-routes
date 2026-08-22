import os
import time

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

YC = "https://bba1p30liradr6hj8olf.containers.yandexcloud.net"
YKEY = os.environ.get("YANDEX_RASP_KEY") or os.environ.get("YANDEX_RASP_API_KEY") or ""


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY), "yc": True})


@app.get("/trains")
def trains():
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    date = (request.args.get("date") or "").strip()
    pax = int(request.args.get("adults") or request.args.get("pax") or 1)
    if not origin or not dest or not date:
        return jsonify({"error": "from, to, date"}), 400
    try:
        r = requests.post(
            YC + "/api/v1/routes/search",
            json={
                "origin": origin,
                "destination": dest,
                "departure_date": date,
                "passengers": pax,
                "allowed_transport": ["train", "bus"],
                "max_transfers": 1,
            },
            timeout=40,
        )
        data = r.json()
        routes = data.get("routes") or data.get("partially_confirmed_routes") or []
        trains_out = []
        for rt in routes:
            segs = rt.get("segments") or []
            first = segs[0] if segs else {}
            last = segs[-1] if segs else {}
            trains_out.append(
                {
                    "number": first.get("number"),
                    "name": " / ".join(
                        filter(None, [((s.get("number") or "") + " " + (s.get("origin") or "")).strip() for s in segs])
                    ),
                    "dep": first.get("departure_time"),
                    "arr": last.get("arrival_time"),
                    "from": first.get("origin") or origin,
                    "to": last.get("destination") or dest,
                    "type": first.get("transport_type") or "train",
                    "has_transfers": bool(rt.get("transfers_count")),
                    "transfer_city": rt.get("transfer_city"),
                    "segments": segs,
                    "warnings": data.get("warnings") or [],
                }
            )
        return jsonify(
            {
                "source": "yandex-cloud",
                "from": origin,
                "to": dest,
                "trains": trains_out,
                "warnings": data.get("warnings") or [],
                "yandex_configured": True,
                "raw_summary": data.get("search_summary"),
            }
        )
    except Exception as e:
        return jsonify({"source": "error", "trains": [], "error": str(e), "yandex_configured": bool(YKEY)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
