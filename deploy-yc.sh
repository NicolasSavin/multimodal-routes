#!/bin/bash
set -e
cd "$HOME"
rm -rf fn-upload fn.zip
mkdir fn-upload
cd fn-upload
curl -fsSL -o app.py https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/app.py
curl -fsSL -o yc_handler.py https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/yc_handler.py
curl -fsSL -o requirements.txt https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/requirements.txt
python3 - <<'PY'
from pathlib import Path
p=Path('app.py')
t=p.read_text()
if 'import json' not in t.split('from datetime')[0]:
    t='import json\n'+t
if '@app.get("/here")' not in t:
    block='''\nHERE_FILE = "/tmp/here.json"\n\ndef here_load():\n    try:\n        with open(HERE_FILE, "r", encoding="utf-8") as f:\n            return json.load(f)\n    except Exception:\n        return []\n\ndef here_save(rows):\n    with open(HERE_FILE, "w", encoding="utf-8") as f:\n        json.dump(rows, f, ensure_ascii=False)\n\ndef today():\n    return datetime.now().strftime("%Y-%m-%d")\n\n@app.get("/here")\ndef here():\n    action = (request.args.get("action") or "list").strip()\n    rows = [x for x in here_load() if x.get("date") == today()]\n    login = (request.args.get("login") or "").strip().lower()\n    if action == "clear" and login:\n        rows = [x for x in rows if x.get("login") != login]\n        here_save(rows)\n        return jsonify({"ok": True, "people": rows})\n    if action == "set":\n        name = (request.args.get("name") or login).strip()\n        hotel = (request.args.get("hotel") or "").strip()\n        city = (request.args.get("city") or "").strip()\n        if not login or not hotel:\n            return jsonify({"ok": False, "error": "login, hotel"}), 400\n        rows = [x for x in rows if x.get("login") != login]\n        rows.append({"login": login, "name": name, "hotel": hotel, "city": city, "date": today(), "ts": int(time.time())})\n        here_save(rows)\n        return jsonify({"ok": True, "people": rows})\n    return jsonify({"ok": True, "date": today(), "people": rows})\n\n'''
    t=t.replace('\nif __name__ == "__main__":', block+'\nif __name__ == "__main__":')
    p.write_text(t)
print('app patched', '@app.get("/here")' in p.read_text())
PY
python3 -c "import zipfile; z=zipfile.ZipFile('$HOME/fn.zip','w'); z.write('app.py'); z.write('yc_handler.py'); z.write('requirements.txt')"
yc serverless function version create \
  --function-id d4e5aa975qllld89nvh0 \
  --runtime python312 \
  --entrypoint yc_handler.handler \
  --memory 256m \
  --execution-timeout 30s \
  --source-path "$HOME/fn.zip" \
  --environment YANDEX_RASP_KEY=bf7820d3-df51-4349-98e3-3fc4a65851db,RZD_ENABLED=1
echo DONE
