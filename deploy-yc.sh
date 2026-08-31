#!/bin/bash
set -e
cd "$HOME"
rm -rf fn-upload fn.zip
mkdir fn-upload
cd fn-upload
curl -fsSL -o app.py https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/app.py
curl -fsSL -o yc_handler.py https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/yc_handler.py
curl -fsSL -o requirements.txt https://raw.githubusercontent.com/NicolasSavin/multimodal-routes/main/api/requirements.txt
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
