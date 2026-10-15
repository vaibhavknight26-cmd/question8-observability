import json
import time
import uuid
import logging
from collections import deque
from threading import Lock

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

EMAIL = "24f2000638@ds.study.iitm.ac.in"
START_TIME = time.monotonic()
LOCK = Lock()
LOGS = deque(maxlen=1000)

REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests received",
)

@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    REQUESTS.inc()

    entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    try:
        response = await call_next(request)
        entry["status_code"] = response.status_code
        return response
    except Exception:
        entry["status_code"] = 500
        entry["level"] = "ERROR"
        raise
    finally:
        with LOCK:
            LOGS.append(entry)
        print(json.dumps(entry), flush=True)

@app.get("/work")
def work(n: int = Query(default=1, ge=0)):
    return {"email": EMAIL, "done": n}

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": max(0.0, time.monotonic() - START_TIME),
    }

@app.get("/logs/tail")
def logs_tail(limit: int = Query(default=10, ge=0, le=1000)):
    with LOCK:
        entries = list(LOGS)
    return entries[-limit:] if limit else []
