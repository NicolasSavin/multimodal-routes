import json
import os
import re
import time
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import unquote
from xml.etree import ElementTree as ET

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
    "ижевск": ["Агрыз", "Новосибирск", "Екатеринбург", "Казань"],
    "агрыз": ["Новосибирск", "Екатеринбург", "Казань"],
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


def norm(num):
    return "".join(ch for ch in str(num or "").upper() if ch.isalnum())


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
    r = requests.get(
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
        timeout=(3, 8),
    )
    try:
        data = r.json()
    except Exception:
        return [], {"http_code": r.status_code, "text": r.text[:180]}
    if r.status_code >= 400 or data.get("error") or data.get("error_code"):
        return [], {
            "http_code": r.status_code,
            "error_code": data.get("error_code") or data.get("error"),
            "text": data.get("text") or data.get("message") or "yandex error",
        }
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
    return out, "ok"


def pick_hubs(origin, dest):
    o, d = origin.lower(), dest.lower()
    names = []
    for key, hubs in HUBS.items():
        if key in o or key in d:
            names.extend(hubs)
    names.extend(DEFAULT_HUBS)
    if "ижевск" in o and "барнаул" in d:
        names = ["Агрыз", "Новосибирск"] + names
    seen, out = set(), []
    for n in names:
        low = n.lower()
        if low in o or low in d or low in seen:
            continue
        seen.add(low)
        out.append(n)
        if len(out) == 4:
            break
    return out


def kind_name(x):
    return x.get("number") or x.get("type") or "рейс"


def stitch(leg1, leg2, hub, note=None):
    a, b = parse_dt(leg1.get("arr")), parse_dt(leg2.get("dep"))
    if not a or not b:
        return None
    wait = int((b - a).total_seconds() / 60)
    if wait < 35 or wait > 18 * 60:
        return None
    d1 = leg1.get("details") or [
        {"number": leg1.get("number"), "type": leg1.get("type"), "from": leg1.get("from"), "to": leg1.get("to"), "dep": leg1.get("dep"), "arr": leg1.get("arr")}
    ]
    d2 = leg2.get("details") or [
        {"number": leg2.get("number"), "type": leg2.get("type"), "from": leg2.get("from"), "to": leg2.get("to"), "dep": leg2.get("dep"), "arr": leg2.get("arr")}
    ]
    details = d1 + d2
    types = {x.get("type") for x in details}
    item = {
        "number": (leg1.get("number") or "") + "+" + (leg2.get("number") or ""),
        "name": kind_name(leg1) + " + " + kind_name(leg2),
        "type": "mixed" if ("train" in types and "bus" in types) else "train",
        "from": leg1.get("from"),
        "to": leg2.get("to"),
        "dep": leg1.get("dep"),
        "arr": leg2.get("arr"),
        "has_transfers": True,
        "hub": hub,
        "wait_min": wait,
        "details": details,
    }
    if note:
        item["hint"] = note
    return item


def compose(origin, dest, date):
    direct, status = yandex_search(origin, dest, date, 25)
    if status != "ok":
        return direct, status
    extra = []
    for hub in pick_hubs(origin, dest):
        a, _ = yandex_search(origin, hub, date, 8)
        b, _ = yandex_search(hub, dest, date, 8)
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
    seen, uniq = set(), []
    for z in extra:
        key = (z.get("dep"), z.get("arr"), z.get("hub"), z.get("number"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(z)
        if len(uniq) >= 14:
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


def parse_group(g):
    typ = str(g.get("CarTypeName") or g.get("CarType") or g.get("carTypeName") or "")
    low = g.get("LowerPlaceQuantity")
    return {
        "car": g.get("CarNumber") or g.get("carNumber") or g.get("Number"),
        "type": typ,
        "available": int(g.get("TotalPlaceQuantity") or g.get("PlaceQuantity") or g.get("Places") or 0),
        "lower": int(low) if low is not None else 0,
        "free": g.get("FreePlaces") or g.get("freePlaces") or "",
        "compartments": g.get("FreePlacesByCompartments") or g.get("freePlacesByCompartments") or [],
        "provider": g.get("Provider") or None,
    }


def rzd_pick(t, *keys):
    for k in keys:
        if t.get(k):
            return t.get(k)
    return None


def rzd_seats(fr, to, date, pax):
    o_code, d_code = rzd_code(fr), rzd_code(to)
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
            "carGrouping": "DontGroup",
            "specialPlacesDemand": "StandardPlacesAndForDisabledPersons",
            "carIssuingType": "Passenger",
            "getByLocalTime": "true",
        },
        headers=RZD_HEADERS,
        timeout=(3, 10),
        verify=False,
    ).json()
    out = {}
    for t in data.get("Trains") or data.get("trains") or []:
        num = t.get("TrainNumber") or t.get("trainNumber")
        groups = [parse_group(g) for g in (t.get("CarGroups") or t.get("carGroups") or [])]
        lower = sum(g["lower"] for g in groups)
        avail = sum(g["available"] for g in groups)
        coupe_lower = sum(g["lower"] for g in groups if "купе" in g["type"].lower() or "coupe" in g["type"].lower())
        out[norm(num)] = {
            "number": num,
            "name": rzd_pick(t, "TrainDescription", "TrainName", "DisplayTrainNumber") or num,
            "from": rzd_pick(t, "OriginName", "OriginStationName") or fr,
            "to": rzd_pick(t, "DestinationName", "DestinationStationName") or to,
            "dep": rzd_pick(t, "DepartureDateTime", "LocalDepartureDateTime", "DepartureDate"),
            "arr": rzd_pick(t, "ArrivalDateTime", "LocalArrivalDateTime", "ArrivalDate"),
            "available": avail,
            "lower": lower,
            "lower_enough": lower >= pax,
            "same_coupe": coupe_lower >= pax or any("купе" in g["type"].lower() and g["available"] >= pax for g in groups),
            "same_coupe_lower": coupe_lower >= pax,
            "groups": groups,
            "origin": o_code,
            "destination": d_code,
            "provider": t.get("Provider") or t.get("provider"),
        }
    return out


def rzd_as_trains(origin, dest, seats):
    out = []
    for s in seats.values():
        out.append(
            {
                "number": s.get("number"),
                "name": s.get("name") or s.get("number"),
                "type": "train",
                "from": s.get("from") or origin,
                "to": s.get("to") or dest,
                "dep": s.get("dep"),
                "arr": s.get("arr"),
                "has_transfers": False,
                "details": [],
                "rzd": s,
                "source": "rzd",
            }
        )
    out.sort(key=lambda z: str(z.get("dep") or ""))
    return out


def rzd_cars(fr, to, date, train, dep=None, provider=None, pax=1):
    seats = rzd_seats(fr, to, date, pax)
    info = seats.get(norm(train)) or {}
    groups = list(info.get("groups") or [])
    if any(g.get("car") or g.get("free") or g.get("compartments") for g in groups):
        return groups, None
    o_code, d_code = rzd_code(fr), rzd_code(to)
    payload = {
        "OriginCode": o_code,
        "DestinationCode": d_code,
        "TrainNumber": train,
        "DepartureDate": (dep or (date + "T00:00:00"))[:19],
        "Provider": provider or info.get("provider") or "P1",
        "SpecialPlacesDemand": "StandardPlacesAndForDisabledPersons",
        "CarIssuingType": "Passenger",
        "OnlyFpkBranded": False,
        "HasPlacesForLargeFamily": False,
    }
    r = requests.post(
        RZD + "/apib2b/p/Railway/V1/Search/CarPricing",
        params={"service_provider": "B2B_RZD", "isBonusPurchase": "false"},
        json=payload,
        headers=RZD_HEADERS,
        timeout=(4, 12),
        verify=False,
    )
    data = r.json() if r.content else {}
    cars = []
    for g in data.get("Cars") or data.get("cars") or []:
        cars.append(parse_group(g) | {"car": g.get("CarNumber") or g.get("Number") or g.get("carNumber")})
    return cars or groups, data.get("error") or None


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "ts": int(time.time()),
            "yandex": bool(YKEY),
            "rzd_enabled": RZD_ON,
            "cars": True,
            "s3": bool(S3_BUCKET),
            "web": True,
        }
    )


@app.get("/suggest")
def suggest():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    d = requests.get("https://suggests.rasp.yandex.net/all_suggests", params={"format": "old", "part": q}, timeout=(2, 5)).json()
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


@app.get("/cars")
def cars():
    try:
        cars_out, err = rzd_cars(
            request.args.get("from") or "",
            request.args.get("to") or "",
            request.args.get("date") or "",
            request.args.get("train") or "",
            request.args.get("dep"),
            request.args.get("provider"),
            int(request.args.get("pax") or 1),
        )
        return jsonify({"cars": cars_out, "error": err})
    except Exception as e:
        return jsonify({"cars": [], "error": str(e)})


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
    have = {norm(item.get("number")) for item in trains_out}
    for item in trains_out:
        key = norm(item.get("number"))
        if key in seats:
            item["rzd"] = seats[key]
    if seats:
        extra = rzd_as_trains(origin, dest, seats)
        for item in extra:
            if norm(item.get("number")) not in have:
                trains_out.append(item)
                have.add(norm(item.get("number")))
    return jsonify(
        {
            "source": "yandex-rasp+hubs+rzd",
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


HERE_FILE = "/tmp/here.json"
TALK_FILE = "/tmp/talk.json"
SOS_FILE = "/tmp/sos.json"
S3_BUCKET = (os.environ.get("S3_BUCKET") or "").strip()
S3_KEY = (os.environ.get("S3_KEY") or os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
S3_SECRET = (os.environ.get("S3_SECRET") or os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()
S3_ENDPOINT = (os.environ.get("S3_ENDPOINT") or "https://storage.yandexcloud.net").rstrip("/")
_IAM = {"t": 0, "token": ""}

HOTELS = [{"n": "У Моста", "a": "", "p": 3000}, {"n": "Шайба", "a": "", "p": 3500}, {"n": "Голландия", "a": "", "p": 3500}, {"n": "Юмья", "a": "", "p": 4000}, {"n": "900км, УЮТ - с Москвы правая сторона", "a": "", "p": 3900}, {"n": "900 км на Москву правая сторона", "a": "", "p": 4000}, {"n": "Милеш (Исаково)", "a": "", "p": 4000}, {"n": "Причал (Мамадыш)", "a": "", "p": 3500}, {"n": "Чибис (Мамадыш)", "a": "", "p": 3500}, {"n": "Дубай", "a": "", "p": 4000}, {"n": "Астория", "a": "", "p": 4000}, {"n": "Кугеси Тракдом", "a": "", "p": 3500}, {"n": "Соло (Пыра)", "a": "", "p": 4000}, {"n": "Слобода", "a": "", "p": 3900}, {"n": "Воротынец", "a": "", "p": 4000}, {"n": "Вертолет", "a": "", "p": 4000}, {"n": "Глобус", "a": "", "p": 3500}, {"n": "Львово", "a": "", "p": 3500}, {"n": "ЯТь", "a": "", "p": 4000}, {"n": "Уют (Ярослав)", "a": "", "p": 4000}, {"n": "Вязники", "a": "", "p": 3500}, {"n": "Вязники (Сытый Гость)", "a": "", "p": 3500}, {"n": "Дубрава", "a": "", "p": 4000}, {"n": "Ямская Слобода", "a": "", "p": 4000}, {"n": "Коурково", "a": "", "p": 4000}, {"n": "УЮТ (объездная Перми)", "a": "", "p": 4000}, {"n": "59 регион (Очер)", "a": "", "p": 3500}, {"n": "У Озера", "a": "", "p": 4000}, {"n": "Барабинск (На Посту)", "a": "", "p": 4000}, {"n": "Тюкалинск (Берлога)", "a": "", "p": 3500}, {"n": "Караван (Омск)", "a": "", "p": 4500}, {"n": "ИП Авагян 943 км (Омская обл)", "a": "", "p": 4500}, {"n": "Ольга (Омская обл, 545 км.)", "a": "", "p": 4000}, {"n": "Кунгур (Вираж)", "a": "", "p": 4000}, {"n": "Дилижанс", "a": "Республика Татарстан, Менделеевский р-н, д. Мунайка, ул. Звёздная, 1", "t": "+7 (917) 921-85-20", "p": 3500, "s": 2500, "img": "https://avatars.mds.yandex.net/get-altay/15434262/2a00000197c7285df95c6759cbbd7faf50e2/XXL_height", "maps": "https://yandex.ru/maps/org/dilizhans/236722142073/"}, {"n": "Аврора", "a": "", "p": 4000}, {"n": "Синявино", "a": "", "p": 3500}, {"n": "Заячья гора", "a": "", "p": 4000}, {"n": "Заячья гора Любава", "a": "", "p": 3900}, {"n": "Курское", "a": "", "p": 4000}, {"n": "Курское (солнечная горка)", "a": "", "p": 3600}, {"n": "Изумрудный город", "a": "", "p": 4000}, {"n": "Агрострой", "a": "", "p": 4000}, {"n": "Эберс", "a": "", "p": 3500}, {"n": "Итель", "a": "", "p": 3500}, {"n": "Орловский родник", "a": "", "p": 4000}, {"n": "Терса", "a": "", "p": 4100}, {"n": "Прага", "a": "", "p": 4100}, {"n": "Тихий Дон", "a": "", "p": 4000}, {"n": "Абацкая слобода", "a": "", "p": 4000}, {"n": "Караван (Сызрань)", "a": "", "p": 4000}, {"n": "Алекс", "a": "", "p": 4000}, {"n": "Каспий", "a": "", "p": 4000}, {"n": "Саквояж", "a": "", "p": 4000}, {"n": "Юрья", "a": "", "p": 3500}, {"n": "Йошкар-Ола", "a": "", "p": 4000}, {"n": "Пермь", "a": "", "p": 4500}, {"n": "Тейково", "a": "", "p": 4000}, {"n": "Дивное место", "a": "", "p": 3500}, {"n": "Коломна", "a": "", "p": 4500}, {"n": "Муром", "a": "", "p": 4500}, {"n": "Фемели", "a": "", "p": 4500}, {"n": "320 км.", "a": "", "p": 3900}, {"n": "Шахты (Дуэт)", "a": "", "p": 4500}, {"n": "Бийск", "a": "", "p": 4500}, {"n": "Новоалтайск", "a": "", "p": 4500}, {"n": "Дзержинский (экодомик)", "a": "", "p": 4500}, {"n": "Мурманск", "a": "", "p": 4500}, {"n": "Дружинино", "a": "", "p": 4500}, {"n": "Екатеринбург (отель Свердлова 27)", "a": "ул. Свердлова, 27", "p": 5500}, {"n": "Нижняя Тура", "a": "", "p": 4500}, {"n": "Саратов", "a": "", "p": 4500}, {"n": "Новосибирск", "a": "", "p": 4500}, {"n": "Владимир", "a": "", "p": 4500}, {"n": "Дивеево", "a": "", "p": 4500}, {"n": "С-Посад (ИП Тимчук)", "a": "", "p": 4500}, {"n": "С-Посад, УЮТ", "a": "", "p": 4700}, {"n": "Волгоград", "a": "", "p": 4500}, {"n": "Плесецк (ласточкино гнездо)", "a": "", "p": 4000}, {"n": "Мирный", "a": "", "p": 4500}, {"n": "Знаменск", "a": "", "p": 4500}, {"n": "Северодвинск", "a": "", "p": 4500}, {"n": "Москва", "a": "", "p": 5500}, {"n": "С-Петербург", "a": "", "p": 5500}]


def hotel_line(h):
    line = h.get("n") or "гостиница"
    if h.get("a"):
        line += " · " + h.get("a")
    else:
        line += " · адреса в карточке сайта нет"
    if h.get("t"):
        line += " · " + h.get("t")
    else:
        line += " · телефона в карточке сайта нет"
    p, s = h.get("p"), h.get("s")
    if p:
        line += " · отчёт " + str(p) + " ₽"
    if s:
        line += " · проживание " + str(s) + " ₽"
    return line


def hotels_named(q):
    low = (q or "").lower().replace("ё", "е")
    hits, seen = [], set()
    for h in HOTELS:
        n = (h.get("n") or "").lower().replace("ё", "е")
        if not n or n in seen:
            continue
        key = re.split(r"[\s(,./]+", n)[0]
        if len(n) >= 3 and n in low:
            hits.append(h)
            seen.add(n)
        elif len(key) >= 4 and re.search(r"(^|[^а-яa-z0-9])" + re.escape(key) + r"([^а-яa-z0-9]|$)", low):
            hits.append(h)
            seen.add(n)
    return hits


def hotels_match(q, limit=14):
    named = hotels_named(q)
    if named:
        return [hotel_line(h) for h in named[:limit]]
    low = (q or "").lower().replace("ё", "е")
    words = [w for w in re.split(r"[^а-яa-z0-9]+", low) if len(w) >= 3]
    skip = {"дай", "дайте", "телефон", "адрес", "гостин", "гостинка", "гостиницы", "отел", "номер", "нужен", "нужна"}
    words = [w for w in words if w not in skip]
    hits = []
    for h in HOTELS:
        blob = " ".join(str(h.get(k) or "") for k in ("n", "a", "c", "t")).lower().replace("ё", "е")
        if words and any(w in blob for w in words):
            hits.append(h)
    out = [hotel_line(h) for h in hits[:limit]]
    return out


def today():
    return datetime.now().strftime("%Y-%m-%d")


def _plain(s):
    s = unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def yandex_web_search(q, limit=6):
    key = (os.environ.get("YANDEX_SEARCH_KEY") or os.environ.get("YANDEX_GPT_KEY") or "").strip()
    folder = os.environ.get("YANDEX_FOLDER") or "b1gsp17rfc7eqhdk6413"
    if not key or not q:
        return []
    r = requests.post(
        "https://searchapi.api.cloud.yandex.net/v2/web/search",
        headers={"Authorization": "Api-Key " + key, "Content-Type": "application/json"},
        json={
            "query": {"searchType": "SEARCH_TYPE_RU", "queryText": q[:180]},
            "folderId": folder,
            "responseFormat": "FORMAT_XML",
        },
        timeout=6,
    )
    js = r.json() if r.content else {}
    raw = js.get("rawData") or ""
    if not raw:
        return []
    xml = base64.b64decode(raw).decode("utf-8", "replace")
    root = ET.fromstring(xml)
    out = []
    for doc in root.iter("doc"):
        url_el = doc.find("url")
        title_el = doc.find("title")
        url = _plain(url_el.text if url_el is not None else "")
        title = _plain("".join(title_el.itertext()) if title_el is not None else "")
        passages = [_plain("".join(p.itertext())) for p in doc.iter("passage")]
        snippet = " ".join([x for x in passages if x])[:320]
        if title or snippet:
            out.append({"title": title, "url": url, "snippet": snippet, "src": "yandex"})
        if len(out) >= limit:
            break
    return out


def wiki_search(q, limit=4):
    r = requests.get(
        "https://ru.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": q[:180],
            "utf8": 1,
            "format": "json",
            "srlimit": limit,
        },
        headers={"User-Agent": "NTC-Okhrana/1.0"},
        timeout=4,
    )
    out = []
    for hit in ((r.json() or {}).get("query") or {}).get("search") or []:
        title = hit.get("title") or ""
        out.append(
            {
                "title": title,
                "url": "https://ru.wikipedia.org/wiki/" + title.replace(" ", "_"),
                "snippet": _plain(hit.get("snippet") or "")[:320],
                "src": "wiki",
            }
        )
    return out


def ddg_search(q, limit=5):
    r = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": q[:180]},
        headers={"User-Agent": "Mozilla/5.0 (compatible; NTC-Okhrana/1.0)"},
        timeout=3,
    )
    html = r.text or ""
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.I | re.S)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|span|div)', html, re.I | re.S)
    urls = re.findall(r"uddg=([^\"&]+)", html)
    n = min(limit, max(len(titles), len(snippets), len(urls)))
    out = []
    for i in range(n):
        title = _plain(titles[i] if i < len(titles) else "")
        snippet = _plain(snippets[i] if i < len(snippets) else "")[:320]
        url = unquote(urls[i]) if i < len(urls) else ""
        if title or snippet:
            out.append({"title": title, "url": url, "snippet": snippet, "src": "ddg"})
    return out


def osm_search(q, limit=4):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": q[:180], "format": "jsonv2", "limit": limit, "accept-language": "ru"},
        headers={"User-Agent": "NTC-Okhrana/1.0"},
        timeout=4,
    )
    out = []
    for hit in r.json() or []:
        title = hit.get("display_name") or hit.get("name") or ""
        lat, lon = hit.get("lat"), hit.get("lon")
        snippet = (hit.get("type") or "") + " · " + (hit.get("addresstype") or "")
        if lat and lon:
            snippet += " · https://yandex.ru/maps/?pt=%s,%s&z=16" % (lon, lat)
        out.append(
            {
                "title": title,
                "url": "https://www.openstreetmap.org/" + (hit.get("osm_type") or "node")[0] + "/" + str(hit.get("osm_id") or ""),
                "snippet": _plain(snippet)[:320],
                "src": "osm",
            }
        )
    return out


def web_ok_for_hotel(row, hotel):
    blob = " ".join(
        str(row.get(k) or "") for k in ("title", "snippet", "url")
    ).lower().replace("ё", "е")
    own = " ".join(str(hotel.get(k) or "") for k in ("n", "a", "c")).lower().replace("ё", "е")
    foreign = (
        "махачкал", "дагестан", "каспийск", "астрахан", "дербент",
        "101hotels", "ostrovok", "sutochno", "tutu.ru", "rzd.ru", "rasp.yandex",
        "booking.com", "яндекс путешеств",
    )
    for bad in foreign:
        if bad in blob and bad not in own:
            return False
    return True


def web_lookup(q, skip_wiki=False):
    q = (q or "").strip()
    if len(q) < 3:
        return [], "skip"
    short = re.sub(
        r"\b(как|доехать|добраться|где|какой|какая|какие|есть|нужно|подскажи|пожалуйста|скажи|можно|телефон|адрес|номер|погода|сайт|официальный|дай|дайте)\b",
        " ",
        q,
        flags=re.I,
    )
    short = re.sub(r"\s+", " ", short).strip() or q
    rows, srcs = [], []
    plan = [(yandex_web_search, q, "yandex"), (osm_search, short, "osm")]
    if not skip_wiki:
        plan.append((wiki_search, short, "wiki"))
    plan.append((ddg_search, short, "ddg"))
    for fn, query, name in plan:
        if name == "ddg" and len(rows) >= 3:
            break
        try:
            got = fn(query) or []
        except Exception:
            got = []
        if got:
            rows.extend(got)
            srcs.append(name)
        if name != "yandex" and len(rows) >= 8:
            break
    seen, uniq = set(), []
    for x in rows:
        k = (x.get("url") or x.get("title") or "")[:90]
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(x)
        if len(uniq) >= 8:
            break
    return uniq, "+".join(srcs) or "none"


def _iam_token():
    if _IAM["token"] and time.time() - _IAM["t"] < 3000:
        return _IAM["token"]
    for url in (
        "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token",
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
    ):
        try:
            r = requests.get(url, headers={"Metadata-Flavor": "Google"}, timeout=2)
            tok = (r.json() or {}).get("access_token") or ""
            if tok:
                _IAM["token"], _IAM["t"] = tok, time.time()
                return tok
        except Exception:
            pass
    return os.environ.get("YC_TOKEN") or ""


def _aws4_headers(method, path, body):
    region, service = "ru-central1", "s3"
    now = datetime.utcnow()
    amz, date = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    payload = hashlib.sha256(body).hexdigest()
    canonical_headers = "host:storage.yandexcloud.net\nx-amz-content-sha256:%s\nx-amz-date:%s\n" % (payload, amz)
    signed = "host;x-amz-content-sha256;x-amz-date"
    canonical = "%s\n%s\n\n%s\n%s\n%s" % (method, path, canonical_headers, signed, payload)
    scope = "%s/%s/%s/aws4_request" % (date, region, service)
    string_to_sign = "AWS4-HMAC-SHA256\n%s\n%s\n%s" % (amz, scope, hashlib.sha256(canonical.encode()).hexdigest())

    def _sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k = _sign(("AWS4" + S3_SECRET).encode("utf-8"), date)
    k = hmac.new(k, region.encode("utf-8"), hashlib.sha256).digest()
    k = hmac.new(k, service.encode("utf-8"), hashlib.sha256).digest()
    k = hmac.new(k, b"aws4_request", hashlib.sha256).digest()
    sig = hmac.new(k, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    auth = "AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s" % (S3_KEY, scope, signed, sig)
    return {
        "Authorization": auth,
        "x-amz-date": amz,
        "x-amz-content-sha256": payload,
        "Content-Type": "application/json",
    }


def _s3_headers(method, path, body):
    if S3_KEY and S3_SECRET:
        return _aws4_headers(method, path, body)
    tok = _iam_token()
    if tok:
        return {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
    return None


def _s3_get(name):
    if not S3_BUCKET:
        return None
    path = "/%s/%s" % (S3_BUCKET, name)
    headers = _s3_headers("GET", path, b"")
    if not headers:
        return None
    try:
        r = requests.get(S3_ENDPOINT + path, headers=headers, timeout=8)
        if r.status_code == 200 and r.content:
            return r.json()
    except Exception:
        pass
    return None


def _s3_put(name, obj):
    if not S3_BUCKET:
        return False
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    path = "/%s/%s" % (S3_BUCKET, name)
    headers = _s3_headers("PUT", path, body)
    if not headers:
        return False
    try:
        r = requests.put(S3_ENDPOINT + path, data=body, headers=headers, timeout=8)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


def _jload(path, default):
    name = str(path).split("/")[-1]
    data = _s3_get(name)
    if data is not None:
        return data
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _jsave(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    except Exception:
        pass
    _s3_put(str(path).split("/")[-1], obj)


def here_load():
    data = _jload(HERE_FILE, {})
    if data.get("date") != today():
        return []
    return data.get("people") or []


def here_save(rows):
    _jsave(HERE_FILE, {"date": today(), "people": rows})


@app.get("/here")
def here():
    action = (request.args.get("action") or "list").strip()
    rows = here_load()
    if action == "clear":
        login = (request.args.get("login") or "").strip().lower()
        rows = [x for x in rows if x.get("login") != login]
        here_save(rows)
        return jsonify({"ok": True, "people": rows})
    if action == "set":
        login = (request.args.get("login") or "").strip().lower()
        name = (request.args.get("name") or login).strip()
        hotel = (request.args.get("hotel") or "").strip()
        city = (request.args.get("city") or "").strip()
        if not login or not hotel:
            return jsonify({"ok": False, "error": "login, hotel"}), 400
        rows = [x for x in rows if x.get("login") != login]
        rows.append(
            {
                "login": login,
                "name": name,
                "hotel": hotel,
                "city": city,
                "date": today(),
                "ts": int(time.time()),
            }
        )
        here_save(rows)
        return jsonify({"ok": True, "people": rows})
    return jsonify({"ok": True, "date": today(), "people": rows})


@app.get("/chat")
def chat():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "q"}), 400
    key = os.environ.get("YANDEX_GPT_KEY") or ""
    folder = os.environ.get("YANDEX_FOLDER") or "b1gsp17rfc7eqhdk6413"
    if not key:
        return jsonify({"ok": False, "text": "", "err": "no YANDEX_GPT_KEY"})
    date = (request.args.get("date") or "").strip()
    low = q.lower().replace("ё", "е")
    if not date:
        base = datetime.now()
        if "послезавтра" in low:
            base = base + timedelta(days=2)
        elif "завтра" in low:
            base = base + timedelta(days=1)
        date = base.strftime("%Y-%m-%d")
    origin = (request.args.get("from") or "").strip()
    dest = (request.args.get("to") or "").strip()
    if not origin or not dest:
        m = re.search(
            r"(?:из\s+)?([а-яё\- ]{3,32}?)\s*(?:—|-|–|до)\s+([а-яё\- ]{3,32})",
            low,
        )
        if not m:
            m = re.search(r"\bиз\s+([а-яё\- ]{3,24}?)\s+в\s+([а-яё\- ]{3,24})", low)
        if m:
            origin = m.group(1).strip(" ?.,")
            dest = m.group(2).strip(" ?.,")
            dest = re.split(r"\s+(на|завтра|послезавтра|сегодня|есть|билет)", dest)[0].strip()
    live = []
    if origin and dest and YKEY:
        try:
            rows, _ = yandex_search(origin, dest, date, 12)
            for t in (rows or [])[:8]:
                live.append(
                    "{num} {typ} {fr} → {to} {dep}–{arr}{xf}".format(
                        num=t.get("number") or "",
                        typ=t.get("type") or "",
                        fr=t.get("from") or origin,
                        to=t.get("to") or dest,
                        dep=str(t.get("dep") or "")[:16],
                        arr=str(t.get("arr") or "")[:16],
                        xf=" · пересадка" if t.get("has_transfers") else "",
                    )
                )
        except Exception:
            pass
    who = []
    try:
        for p in here_load()[:12]:
            who.append("{n} — {h} ({c})".format(n=p.get("name") or p.get("login"), h=p.get("hotel"), c=p.get("city") or ""))
    except Exception:
        pass
    named = hotels_named(q)
    web_rows, web_src = [], "none"
    try:
        if named:
            h0 = named[0]
            web_q = 'гостиница "{name}" {addr} телефон мотель трасса дальнобойщиков'.format(
                name=h0.get("n") or "",
                addr=h0.get("a") or h0.get("c") or "",
            )
            web_rows, web_src = web_lookup(web_q, skip_wiki=True)
            web_rows = [w for w in web_rows if web_ok_for_hotel(w, h0)]
            if not web_rows:
                web_src = web_src + "+filtered"
        else:
            web_rows, web_src = web_lookup(q)
    except Exception:
        web_rows, web_src = [], "err"
    sys = (
        "Ты помощник командировок внутреннего сайта «НТЦ Охрана / Команда охрана грузов». "
        "Это не касса. Запрещено писать «нет доступа к билетам». "
        "Запрещено отправлять на tutu, rzd, rasp.yandex.ru, 101hotels, ostrovok, booking, яндекс путешествия. "
        "Сначала данные сайта: рейсы, раздел Гостиницы, кто где сегодня. "
        "Если названа гостиница из раздела Гостиницы — это ЕДИНСТВЕННАЯ нужная точка. "
        "Не подменяй её одноимённым отелем в другом городе. Пример: «Каспий» из списка — не гостиница в Махачкале. "
        "Интернет — только чтобы дополнить ТУ ЖЕ карточку (телефон, адрес). "
        "Если в сети другая точка с тем же названием — игнорируй. "
        "Если телефона нет в карточке и нет в проверенном интернете — скажи прямо: "
        "в списке Гостиницы такая есть, телефона в карточке нет, именно эту точку в сети не нашёл. "
        "Не выдумывай номер. Билеты не продаёшь. Маршруты — раздел Маршруты этого сайта. "
        "Отвечай по-русски коротко и по делу."
    )
    extra = ["Дата поиска: " + date]
    if origin and dest:
        extra.append("Направление: " + origin + " → " + dest)
    if live:
        extra.append("Живые рейсы с сайта:\n" + "\n".join(live))
    elif origin and dest:
        extra.append("Живых рейсов сейчас нет или направление не распознано.")
    if who:
        extra.append("Сегодня отметились:\n" + "\n".join(who))
    if named:
        extra.append(
            "Точная гостиница из раздела Гостиницы (сотрудник имеет в виду её, не тёзку):\n"
            + "\n".join(hotel_line(h) for h in named)
        )
    else:
        hs = hotels_match(" ".join([q, origin or "", dest or ""]))
        if hs:
            extra.append("Гостиницы из списка сайта:\n" + "\n".join(hs))
    if web_rows:
        lines = []
        for i, w in enumerate(web_rows, 1):
            bit = (w.get("title") or "") + " — " + (w.get("snippet") or "")
            if w.get("url"):
                bit += " (" + w.get("url") + ")"
            lines.append(str(i) + ". " + bit[:420])
        extra.append("Интернет, только как дополнение к карточке сайта (" + web_src + "):\n" + "\n".join(lines))
    elif named:
        extra.append("Интернет по этой карточке ничего своего не дал. Чужие тёзки отброшены. Не подставляй другой город.")
    user = q + "\n\n" + "\n".join(extra)
    r = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={"Authorization": "Api-Key " + key, "Content-Type": "application/json"},
        json={
            "modelUri": "gpt://" + folder + "/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": "1600"},
            "messages": [
                {"role": "system", "text": sys},
                {"role": "user", "text": user},
            ],
        },
        timeout=25,
    )
    text = ""
    err = ""
    try:
        js = r.json()
        text = js["result"]["alternatives"][0]["message"]["text"]
    except Exception:
        err = (r.text or "")[:400]
    return jsonify(
        {
            "ok": bool(text),
            "text": text,
            "status": r.status_code,
            "err": err,
            "found": len(live),
            "web": len(web_rows),
            "web_src": web_src,
        }
    )


@app.get("/talk")
@app.post("/talk")
def talk():
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or request.args.get("action") or "list").strip()
    rows = _jload(TALK_FILE, [])
    if action == "send":
        login = (data.get("login") or request.args.get("login") or "").strip().lower()
        name = (data.get("name") or request.args.get("name") or login).strip()
        text = (data.get("text") or request.args.get("text") or "").strip()
        media = data.get("media") or ""
        kind = data.get("kind") or ""
        if media and len(str(media)) > 1200000:
            return jsonify({"ok": False, "error": "file too big"}), 400
        if not login or (not text and not media):
            return jsonify({"ok": False, "error": "empty"}), 400
        rows.append(
            {
                "login": login,
                "name": name,
                "text": text[:2000],
                "media": media,
                "kind": kind,
                "ts": int(time.time()),
            }
        )
        rows = rows[-60:]
        _jsave(TALK_FILE, rows)
    return jsonify({"ok": True, "messages": rows})


@app.get("/sos")
@app.post("/sos")
def sos():
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or request.args.get("action") or "list").strip()
    cur = _jload(SOS_FILE, {"on": False})
    if action == "set":
        cur = {
            "on": True,
            "login": (data.get("login") or request.args.get("login") or "").strip().lower(),
            "name": (data.get("name") or request.args.get("name") or "").strip(),
            "note": (data.get("note") or request.args.get("note") or "").strip()[:300],
            "ts": int(time.time()),
        }
        _jsave(SOS_FILE, cur)
    elif action == "clear":
        cur = {"on": False, "ts": int(time.time())}
        _jsave(SOS_FILE, cur)
    return jsonify({"ok": True, "sos": cur})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
