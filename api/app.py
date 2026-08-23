import os
import time

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

YKEY = os.environ.get("YANDEX_RASP_KEY") or os.environ.get("YANDEX_RASP_API_KEY") or ""
RZD_ON = os.environ.get("RZD_ENABLED", "0").lower() in {"1", "true", "yes"}
RZD = "https://ticket.rzd.ru"
RZD_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://ticket.rzd.ru/",
}


def yandex_code(q):
    d = requests.get(
        "https://suggests.rasp.yandex.net/all_suggests",
        params={"format": "old", "part": q},
        timeout=(3, 6),
    ).json()
    rows = (d or [None, []])[1] or []
    city = None
    station = None
    for row in rows:
        if not row:
            continue
        code = str(row[0])
        title = row[1]
        if code.startswith("c") and city is None:
            city = (code, title)
        if code.startswith("s") and station is None:
            station = (code, title)
    if city:
        return city
    if station:
        return station
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
            "limit": 40,
            "transport_types": "train,bus",
            "transfers": "yes",
        },
        timeout=(3, 12),
    ).json()
    out = []
    for s in data.get("segments") or []:
        th = s.get("thread") or {}
        details = []
        for p in s.get("details") or []:
            if not isinstance(p, dict):
                continue
            pth = p.get("thread") or {}
            if not (pth or p.get("departure")):
                continue
            details.append(
                {
                    "number": pth.get("number"),
                    "type": pth.get("transport_type") or p.get("transport_type"),
                    "from": (p.get("from") or {}).get("title"),
                    "to": (p.get("to") or {}).get("title"),
                    "dep": p.get("departure"),
                    "arr": p.get("arrival"),
                }
            )
        types = {d.get("type") for d in details}
        mixed = "train" in types and "bus" in types
        out.append(
            {
                "number": th.get("number"),
                "name": th.get("title"),
                "type": "mixed" if mixed else (th.get("transport_type") or "train"),
                "from": (s.get("from") or {}).get("title") or an,
                "to": (s.get("to") or {}).get("title") or bn,
                "dep": s.get("departure"),
                "arr": s.get("arrival"),
                "has_transfers": bool(s.get("has_transfers")) or len(details) > 1,
                "details": details,
            }
        )
    return out, data.get("error") or "ok"


def rzd_code(q):
    data = requests.get(
        RZD + "/isdk/suggests",
        params={"Query": q, "TransportType": "rail", "GroupResults": "true", "Language": "ru"},
        headers=RZD_HEADERS,
        timeout=(3, 6),
        verify=False,
    ).json()
    for n in data.get("transport_node_suggests") or []:
        codes = n.get("Codes") or {}
        code = codes.get("Railway") or n.get("code")
        if code:
            return str(code)
    raise ValueError("no rzd code")


def rzd_seats(fr, to, date, pax):
    o_code = rzd_code(fr)
    d_code = rzd_code(to)
    data = requests.get(
        RZD + "/api/v1/railway-service/prices/train-pricing",
        params={
            "service_provider": "B2B_RZD",
            "origin": o_code,
            "destination": d_code,
            "departureDate": date + "T00:00:00",
            "adultPassengersQuantity": pax,
            "childrenPassengersQuantity": 0,
            "getTrainsFromSchedule": "true",
            "carGrouping": "Group",
            "specialPlacesDemand": "StandardPlacesAndForDisabledPersons",
            "carIssuingType": "Passenger",
            "getByLocalTime": "true",
        },
        headers=RZD_HEADERS,
        timeout=(3, 8),
        verify=False,
    ).json()
    out = {}
    for t in data.get("Trains") or data.get("trains") or []:
        num = t.get("TrainNumber") or t.get("trainNumber")
        lower = avail = coupe_lower = 0
        for g in t.get("CarGroups") or t.get("carGroups") or []:
            avail += int(g.get("TotalPlaceQuantity") or g.get("PlaceQuantity") or 0)
            low = g.get("LowerPlaceQuantity")
            low_n = int(low) if low is not None else 0
            lower += low_n
            typ = str(g.get("CarTypeName") or g.get("CarType") or "").lower()
            if "купе" in typ or "coupe" in typ:
                coupe_lower += low_n
        key = "".join(ch for ch in str(num or "").upper() if ch.isalnum())
        out[key] = {
            "number": num,
            "available": avail,
            "lower": lower,
            "lower_enough": lower >= pax,
            "same_coupe_lower": coupe_lower >= pax,
        }
    return out


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "ts": int(time.time()),
            "yandex": bool(YKEY),
            "rzd_enabled": RZD_ON,
            "region": "yc",
        }
    )


@app.get("/suggest")
def suggest():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    d = requests.get(
        "https://suggests.rasp.yandex.net/all_suggests",
        params={"format": "old", "part": q},
        timeout=(2, 5),
    ).json()
    out = []
    seen = set()
    for row in (d or [None, []])[1] or []:
        if not row:
            continue
        title = str(row[1])
        if title in seen:
            continue
        seen.add(title)
        out.append({"title": title, "code": row[0]})
        if len(out) >= 12:
            break
    return jsonify(out)


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

    seats, seats_err = {}, None
    if RZD_ON:
        try:
            seats = rzd_seats(origin, dest, date, pax)
        except Exception as e:
            seats_err = str(e)
    else:
        seats_err = "rzd_off"

    for item in trains_out:
        key = "".join(ch for ch in str(item.get("number") or "").upper() if ch.isalnum())
        if key in seats:
            item["rzd"] = seats[key]

    return jsonify(
        {
            "source": "yandex-rasp",
            "from": origin,
            "to": dest,
            "trains": trains_out,
            "status": status,
            "error": err,
            "rzd_error": seats_err,
            "rzd_trains": len(seats),
            "rzd_enabled": RZD_ON,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
