from fastapi import FastAPI
from oncolake.lake import storage
from oncolake.config.settings import settings
import time
from oncolake.ingest import alphafold
from oncolake.features.extract import features_for_record
from oncolake.schemas import IngestRequest
from oncolake.ingest.fast import ingest_fast

app = FastAPI(title="OncoLake API")


@app.get("/health")
def health():
    return {"minio_ok": storage.ping()}

@app.get("/stats")
def stats():
    buckets = {}
    for b in settings.buckets:             
        buckets[b] = storage.count_objects(b)
    return buckets

def _list_zone(bucket: str):
    return {"zone": bucket, "objets": storage.list_keys(bucket)}


@app.get("/raw")
def raw():
    return _list_zone(settings.bucket_raw)

@app.get("/staging")
def staging():
    return _list_zone(settings.bucket_staging)

@app.get("/curated")
def curated():
    return _list_zone(settings.bucket_curated)


@app.post("/ingest")
def ingest(req: IngestRequest):     
    start = time.perf_counter()
    features = []
    for item in req.items:
        cif = alphafold.fetch_cif(item.accession)
        if cif is None:
            continue                       
        record = {"accession": item.accession, "sequence": item.sequence,
                  "gene": None, "label": None}
        features.append(features_for_record(record, cif))
    elapsed = time.perf_counter() - start
    # TODO 4b : renvoyer un dict avec n_processed, elapsed_seconds (arrondi à 3), features
    return {"n_processed": len(features), "elapsed_seconds": round(elapsed, 3), "features": features}

@app.post("/ingest_fast")
def ingest_fast_endpoint(req: IngestRequest):
    start = time.perf_counter()
    features = ingest_fast(req.items)
    elapsed = time.perf_counter() - start
    return {"n_processed": len(features), "elapsed_seconds": round(elapsed, 3), "features": features}