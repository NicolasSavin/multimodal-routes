import os
import time
from datetime import datetime, timedelta

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

HUBS = {
    "ижевск": ["Агрыз", "Екатеринбург", "Казань"],
    "агрыз": ["Екатеринбург", "Новосибирск", "Казань"],
    "барнаул": ["Новосибирск", "Екатеринбург"],
}
DEFAULT_HUBS = ["Екатеринбург", "Новосибирск", "Казань"]


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def yandex_code(q):
    d = requests.get(
        "https://suggests.rasp.yandex.net/all_suggests",
        params={"format": "old", "part": q},
        timeout=(3, 6),
    ).json()
    rows = (d or [None, []])[1] or []
    city = station = None
    for row in rows:
        if not row:
            continue
        code, title = str(row[0]), row[1]
        if code.startswith("c") and city is None:
            city = (code, title)
        if code.startswith("s") and station is None:
            station = (code, title)
    return city or station or (None, q)


def yandex_search(fr, to, date, limit=20):
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
            "limit": limit,
            "transport_types": "train,bus",
            "transfers": "yes",
        },
        timeout=(3, 10),
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
        item = {
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
        out.append(item)
    return out, data.get("error") or "ok"


def pick_hubs(origin, dest):
    o = origin.lower()
    d = dest.lower()
    names = []
    for key, hubs in HUBS.items():
        if key in o or key in d:
            names.extend(hubs)
    names.extend(DEFAULT_HUBS)
    seen = set()
    out = []
    for n in names:
        low = n.lower()
        if low in o or low in d or low in seen:
            continue
        seen.add(low)
        out.append(n)
        if len(out) == 3:
            break
    return out


def stitch(leg1, leg2, hub):
    a = parse_dt(leg1.get("arr"))
    b = parse_dt(leg2.get("dep"))
    if not a or not b:
        return None
    wait = int((b - a).total_seconds() / 60)
    if wait < 35 or wait > 16 * 60:
        return None
    d1 = leg1.get("details") or [
        {
            "number": leg1.get("number"),
            "type": leg1.get("type"),
            "from": leg1.get("from"),
            "to": leg1.get("to"),
            "dep": leg1.get("dep"),
            "arr": leg1.get("arr"),
        }
    ]
    d2 = leg2.get("details") or [
        {
            "number": leg2.get("number"),
            "type": leg2.get("type"),
            "from": leg2.get("from"),
            "to": leg2.get("to"),
            "dep": leg2.get("dep"),
            "arr": leg2.get("arr"),
        }
    ]
    details = d1 + d2
    types = {x.get("type") for x in details}
    mixed = "train" in types and "bus" in types
    return {
        "number": (leg1.get("number") or "") + "+" + (leg2.get("number") or ""),
        "name": (leg1.get("name") or kind_name(leg1)) + " + " + (leg2.get("name") or kind_name(leg2)),
        "type": "mixed" if mixed else "train",
        "from": leg1.get("from"),
        "to": leg2.get("to"),
        "dep": leg1.get("dep"),
        "arr": leg2.get("arr"),
        "has_transfers": True,
        "hub": hub,
        "wait_min": wait,
        "details": details,
    }


def kind_name(x):
    return x.get("number") or x.get("type") or "рейс"


def compose(origin, dest, date):
    direct, status = yandex_search(origin, dest, date, 25)
    extra = []
    for hub in pick_hubs(origin, dest):
        a, _ = yandex_search(origin, hub, date, 8)
        b, _ = yandex_search(hub, dest, date, 8)
        # next calendar day for late arrivals
        try:
            nxt = (datetime.fromisoformat(date) + timedelta(days=1)).date().isoformat()
            b2, _ = yandex_search(hub, dest, nxt, 6)
            b = b + b2
        except Exception:
            pass
        for x in a[:6]:
            for y in b[:6]:
                item = stitch(x, y, hub)
                if item:
                    extra.append(item)
    extra.sort(key=lambda z: z.get("dep") or "")
    seen = set()
    uniq = []
    for z in extra:
        key = (z.get("dep"), z.get("arr"), z.get("hub"), z.get("number"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(z)
        if len(uniq) >= 12:
            break
    return direct + uniq, status


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
    return jsonify({"ok": True, "ts": int(time.time()), "yandex": bool(YKEY), "rzd_enabled": RZD_ON, "compose": True})


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
    out, seen = [], set()
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
        trains_out, status = compose(origin, dest, date)
    except Exception as e:
        err = str(e)
    seats, seats_err = {}, None
    if RZD_ON:
        try:
            seats = rzd_seats(origin, dest, date, pax)
        except Exception as e:
            seats_err = str(e)
    for item in trains_out:
        key = "".join(ch for ch in str(item.get("number") or "").upper() if ch.isalnum())
        if key in seats:
            item["rzd"] = seats[key]
    return jsonify(
        {
            "source": "yandex-rasp+hubs",
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
