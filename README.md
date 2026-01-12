# Image Pipeline (FastAPI) - Day5 MVP

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
uvicorn app.main:app --reload --port 9002
```

## Health

GET [http://localhost:9002/pipeline/v1/health](http://localhost:9002/pipeline/v1/health)

## Process

POST [http://localhost:9002/pipeline/v1/process](http://localhost:9002/pipeline/v1/process)

Example body:

```json
{
  "requestId": "req_xxx",
  "sessionId": "sess_123",
  "attemptIndex": 0,
  "rawPath": "D:/booth/data/raw/sess_123/0.jpg",
  "template": {
    "templateId": "tpl_001",
    "outputWidth": 1800,
    "outputHeight": 1200,
    "backgroundPath": "D:/booth/templates/tpl_001/bg.jpg",
    "overlayPath": "D:/booth/templates/tpl_001/overlay.png",
    "safeArea": { "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8 },
    "cropMode": "FILL"
  }
}
```

Preview/Final will be accessible by:

* [http://localhost:9002/files/preview/{sessionId}/{attemptIndex}.jpg](http://localhost:9002/files/preview/{sessionId}/{attemptIndex}.jpg)
* [http://localhost:9002/files/final/{sessionId}/{attemptIndex}.jpg](http://localhost:9002/files/final/{sessionId}/{attemptIndex}.jpg)

## Test

```bash
pytest -q
```
