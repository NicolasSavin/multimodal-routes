import os
import time
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

YKEY = os.environ.get("YANDEX_RASP_KEY") or os.environ.get("YANDEX_RASP_API_KEY") or ""
RZD = "https://ticket.rzd.ru"
RZD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ticket.rzd.ru/",
    "Origin": "https://ticket.rzd.ru",
}
HUBS = [
    "Москва",
    "Казань",
    "Нижний Новгород",
    "Самара",
    "Пермь",
    "Екатеринбург",
    "Уфа",
    "Новосибирск",
    "Челябинск",
    "Киров",
]


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


def _parse_seg(s):
    th = s.get("thread") or {}
    return {
        "number": th.get("number"),
        "name": th.get("title"),
        "type": th.get("transport_type") or "train",
        "from": (s.get("from") or {}).get("title"),
        "to": (s.get("to") or {}).get("title"),
        "dep": s.get("departure"),
        "arr": s.get("arrival"),
        "has_transfers": bool(s.get("has_transfers")),
        "details": [
            {
                "number": ((p.get("thread") or {}).get("number")),
                "type": ((p.get("thread") or {}).get("transport_type")) or p.get("transport_type"),
                "from": (p.get("from") or {}).get("title"),
                "to": (p.get("to") or {}).get("title"),
                "dep": p.get("departure"),
                "arr": p.get("arrival"),
            }
            for p in (s.get("details") or [])
            if isinstance(p, dict) and (p.get("thread") or p.get("departure"))
        ],
    }


def yandex_search(fr, to, date, types="train,bus", transfers="yes"):
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
            "limit": 30,
            "transport_types": types,
            "transfers": transfers,
        },
        timeout=14,
    ).json()
    out = []
    for s in data.get("segments") or []:
        item = _parse_seg(s)
        item["from"] = item["from"] or an
        item["to"] = item["to"] or bn
        out.append(item)
    return out, data.get("error") or "ok"


def _when(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def mix_hub(origin, dest, date):
    mixed = []
    o = origin.strip().lower()
    d = dest.strip().lower()
    for hub in HUBS:
        if hub.lower() in {o, d}:
            continue
        try:
            trains, _ = yandex_search(origin, hub, date, "train", "no")
            buses, _ = yandex_search(hub, dest, date, "bus", "no")
        except Exception:
            continue
        for tr in trains[:4]:
            ta = _when(tr.get("arr"))
            if not ta:
                continue
            for bu in buses[:6]:
                bd = _when(bu.get("dep"))
                if not bd:
                    continue
                wait = (bd - ta).total_seconds() / 60
                if 40 <= wait <= 10 * 60:
                    mixed.append(
                        {
                            "number": (tr.get("number") or "") + "+авто",
                            "name": "Поезд + автобус через " + hub,
                            "type": "mixed",
                            "from": tr.get("from") or origin,
                            "to": bu.get("to") or dest,
                            "dep": tr.get("dep"),
                            "arr": bu.get("arr"),
                            "has_transfers": True,
                            "hub": hub,
                            "wait_min": int(wait),
                            "details": [
                                {
                                    "number": tr.get("number"),
                                    "type": "train",
                                    "from": tr.get("from"),
                                    "to": tr.get("to") or hub,
                                    "dep": tr.get("dep"),
                                    "arr": tr.get("arr"),
                                },
                                {
                                    "number": bu.get("number"),
                                    "type": "bus",
                                    "from": bu.get("from") or hub,
                                    "to": bu.get("to"),
                                    "dep": bu.get("dep"),
                                    "arr": bu.get("arr"),
                                },
                            ],
                        }
                    )
                    if len(mixed) >= 8:
                        return mixed
                    break
    return mixed


def rzd_code(q):
    data = requests.get(
        RZD + "/isdk/suggests",
        params={"Query": q, "TransportType": "rail", "GroupResults": "true", "Language": "ru"},
        headers=RZD_HEADERS,
        timeout=8,
    ).json()
    for n in data.get("transport_node_suggests") or []:
        codes = n.get("Codes") or n.get("codes") or {}
        code = codes.get("Railway") or codes.get("railway") or n.get("code")
        if code:
            return str(code), n.get("Name") or n.get("name") or q
    raise ValueError("RZD station not found: " + q)


def rzd_seats(fr, to, date, pax):
    o_code, _ = rzd_code(fr)
    d_code, _ = rzd_code(to)
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
        timeout=12,
    ).json()
    out = {}
    for t in data.get("Trains") or data.get("trains") or []:
        num = t.get("TrainNumber") or t.get("trainNumber")
        lower = avail = coupe_lower = 0
        for g in t.get("CarGroups") or t.get("carGroups") or []:
            places = int(g.get("TotalPlaceQuantity") or g.get("PlaceQuantity") or 0)
            low = g.get("LowerPlaceQuantity")
            low_n = int(low) if low is not None else 0
            avail += places
            lower += low_n
            typ = str(g.get("CarTypeName") or g.get("CarType") or "").lower()
            if "купе" in typ or typ in {"coupe", "compartment", "куп"}:
                coupe_lower += low_n
        out[_norm(num)] = {
            "number": num,
            "available": avail,
            "lower": lower,
            "lower_enough": lower >= pax,
            "same_coupe_lower": coupe_lower >= pax,
            "same_coupe": coupe_lower >= pax,
        }
    return {"ok": True, "map": out}


def _norm(n):
    return "".join(ch for ch in str(n or "").upper() if ch.isalnum())


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY), "region": "eu"})


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
        a, status = yandex_search(origin, dest, date, "train,bus", "yes")
        b, _ = yandex_search(origin, dest, date, "train", "no")
        c, _ = yandex_search(origin, dest, date, "bus", "no")
        seen = set()
        for item in a + b + c:
            key = (item.get("number"), item.get("dep"), item.get("type"))
            if key in seen:
                continue
            seen.add(key)
            trains_out.append(item)
        if request.args.get("mix", "1") != "0":
            trains_out.extend(mix_hub(origin, dest, date))
    except Exception as e:
        err = str(e)
    seats, seats_err = {}, None
    try:
        raw = rzd_seats(origin, dest, date, pax)
        seats = raw.get("map") or {}
    except Exception as e:
        seats_err = str(e)
    for item in trains_out:
        hit = seats.get(_norm(item.get("number")))
        if hit:
            item["rzd"] = hit
    return jsonify(
        {
            "source": "yandex-rasp+rzd",
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
