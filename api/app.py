import os
import time

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

RZD = "https://ticket.rzd.ru"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://ticket.rzd.ru/",
    "Origin": "https://ticket.rzd.ru",
}
YKEY = os.environ.get("YANDEX_RASP_KEY", "")


def rzd_get(path, params=None, timeout=25):
    r = requests.get(RZD + path, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    if not r.content:
        return {}
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:500]}


def rzd_post(path, json_body, params=None, timeout=25):
    r = requests.post(RZD + path, params=params, json=json_body, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def station_code(q):
    data = rzd_get(
        "/isdk/suggests",
        {"Query": q, "TransportType": "rail", "GroupResults": "true", "Language": "ru"},
    )
    nodes = data.get("transport_node_suggests") or []
    for n in nodes:
        codes = (n.get("Codes") or n.get("codes") or {})
        code = codes.get("Railway") or codes.get("railway") or n.get("code")
        name = n.get("Name") or n.get("name") or n.get("title") or q
        if code:
            return str(code), name, n
    raise ValueError("Станция не найдена: " + q)


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": int(time.time())})


@app.get("/suggest")
def suggest():
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify([])
    try:
        data = rzd_get(
            "/isdk/suggests",
            {"Query": q, "TransportType": "rail", "GroupResults": "true", "Language": "ru"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    out, seen = [], set()
    for n in data.get("transport_node_suggests") or []:
        codes = n.get("Codes") or n.get("codes") or {}
        code = str(codes.get("Railway") or codes.get("railway") or n.get("code") or "")
        name = n.get("Name") or n.get("name") or n.get("title") or ""
        if not code or code in seen:
            continue
        seen.add(code)
        out.append({"code": code, "name": name, "region": n.get("Region") or n.get("region")})
    return jsonify(out[:20])


@app.get("/trains")
def trains():
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    date = (request.args.get("date") or "").strip()
    adults = int(request.args.get("adults") or 1)
    if not origin or not dest or not date:
        return jsonify({"error": "from, to, date обязательны"}), 400
    try:
        o_code, o_name, _ = station_code(origin)
        d_code, d_name, _ = station_code(dest)
        dep = date + "T00:00:00"
        data = rzd_get(
            "/api/v1/railway-service/prices/train-pricing",
            {
                "service_provider": "B2B_RZD",
                "origin": o_code,
                "destination": d_code,
                "departureDate": dep,
                "adultPassengersQuantity": adults,
                "childrenPassengersQuantity": 0,
                "getTrainsFromSchedule": "true",
                "carGrouping": "Group",
                "specialPlacesDemand": "StandardPlacesAndForDisabledPersons",
                "carIssuingType": "Passenger",
                "getByLocalTime": "true",
            },
        )
    except Exception as e:
        y = yandex_search(origin, dest, date)
        return jsonify({"source": "yandex", "error_rzd": str(e), "from": origin, "to": dest, "trains": y})
    trains_out = []
    for t in data.get("Trains") or data.get("trains") or []:
        groups = []
        for g in t.get("CarGroups") or t.get("carGroups") or []:
            groups.append(
                {
                    "type": g.get("CarTypeName") or g.get("CarType") or g.get("ServiceClass"),
                    "places": g.get("TotalPlaceQuantity") or g.get("PlaceQuantity"),
                    "lower": g.get("LowerPlaceQuantity"),
                    "upper": g.get("UpperPlaceQuantity"),
                    "lower_side": g.get("LowerSidePlaceQuantity"),
                    "upper_side": g.get("UpperSidePlaceQuantity"),
                    "min_price": g.get("MinPrice") or g.get("Price"),
                    "same_compartment": (g.get("LowerPlaceQuantity") or 0) + (g.get("UpperPlaceQuantity") or 0) >= 2,
                }
            )
        trains_out.append(
            {
                "number": t.get("TrainNumber"),
                "name": t.get("TrainName") or t.get("TrainDescription"),
                "from_code": t.get("OriginStationCode"),
                "to_code": t.get("DestinationStationCode"),
                "dep": t.get("LocalDepartureDateTime") or t.get("DepartureDateTime"),
                "arr": t.get("LocalArrivalDateTime") or t.get("ArrivalDateTime"),
                "duration_min": t.get("TripDuration"),
                "provider": t.get("Provider"),
                "groups": groups,
            }
        )
    return jsonify({"source": "rzd", "from": o_name, "to": d_name, "from_code": o_code, "to_code": d_code, "trains": trains_out})


@app.post("/cars")
def cars():
    body = request.get_json(force=True, silent=True) or {}
    try:
        data = rzd_post(
            "/apib2b/p/Railway/V1/Search/CarPricing",
            {
                "OriginCode": body.get("origin"),
                "DestinationCode": body.get("destination"),
                "TrainNumber": body.get("train"),
                "DepartureDate": body.get("date"),
                "Provider": body.get("provider") or "P1",
                "SpecialPlacesDemand": "StandardPlacesAndForDisabledPersons",
                "CarIssuingType": "Passenger",
                "OnlyFpkBranded": False,
                "HasPlacesForLargeFamily": False,
            },
            {"service_provider": "B2B_RZD", "isBonusPurchase": "false"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    cars_out = []
    for c in data.get("Cars") or data.get("cars") or []:
        cars_out.append(
            {
                "number": c.get("CarNumber") or c.get("Number"),
                "type": c.get("CarTypeName") or c.get("CarType"),
                "free": c.get("FreePlaces"),
                "by_coupe": c.get("FreePlacesByCompartments"),
                "places": c.get("PlaceQuantity"),
                "lower": c.get("LowerPlaceQuantity"),
                "upper": c.get("UpperPlaceQuantity"),
                "price": c.get("MinPrice") or c.get("Price"),
            }
        )
    return jsonify({"train": data.get("TrainInfo"), "cars": cars_out})


def yandex_search(fr, to, date):
    if not YKEY:
        return []
    try:
        sug = requests.get("https://suggests.rasp.yandex.net/all_suggests", params={"format": "old", "part": fr}, timeout=15).json()
        to_sug = requests.get("https://suggests.rasp.yandex.net/all_suggests", params={"format": "old", "part": to}, timeout=15).json()

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
            params={"apikey": YKEY, "from": a, "to": b, "date": date, "lang": "ru_RU", "limit": 20, "transport_types": "train,bus"},
            timeout=20,
        ).json()
        out = []
        for s in data.get("segments") or []:
            th = s.get("thread") or {}
            out.append({
                "number": th.get("number"),
                "name": th.get("title"),
                "dep": s.get("departure"),
                "arr": s.get("arrival"),
                "from": (s.get("from") or {}).get("title"),
                "to": (s.get("to") or {}).get("title"),
                "type": th.get("transport_type"),
                "groups": [],
            })
        return out
    except Exception:
        return []


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
