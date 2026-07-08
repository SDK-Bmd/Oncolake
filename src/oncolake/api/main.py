from fastapi import FastAPI
from oncolake.lake import storage
from oncolake.config.settings import settings
import time
from oncolake.ingest import alphafold
from oncolake.features.extract import features_for_record
from oncolake.schemas import IngestRequest

app = FastAPI(title="OncoLake API")


@app.get("/health")
def health():
    return {"minio_ok": storage.ping()}

@app.get("/stats")
def stats():
    # TODO : renvoyer {bucket: nombre d'objets} pour les 3 zones
    #   indice boucle : { b: storage.count_objects(b) for b in settings.buckets }
    buckets = {}
    for b in settings.buckets:              # b = "raw", puis "staging", puis "curated"
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