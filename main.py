# -*- coding: utf-8 -*-
import os, json
import psycopg2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NASA Earth Information Jukebox API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATABASE_URL = os.environ.get("DATABASE_URL", "")

with open(os.path.join(os.path.dirname(__file__), "meta.json"), "r", encoding="utf-8") as f:
    META_DATA = json.load(f)

@app.get("/health")
def health():
    # Cron-job burayı çağırır: Render'ı uyanık tutar, Neon kotasını harcamaz!
    return {"status": "ok", "layers": len(META_DATA.get("layers", {}))}

@app.get("/api/meta")
def get_meta():
    return META_DATA

@app.get("/api/point-sonify")
def point_sonify(
    id: int = Query(None, ge=0, lt=12960),
    lat: float = Query(None, ge=-90.0, le=90.0),
    lon: float = Query(None, ge=-180.0, le=180.0)
):
    if id is None:
        if lat is None or lon is None:
            raise HTTPException(400, "id veya (lat, lon) parametresi gerekli.")
        i_lat = min(89, max(0, int((lat + 90.0) // 2.0)))
        i_lon = min(143, max(0, int(((lon + 180.0) % 360.0) // 2.5)))
        id = i_lat * 144 + i_lon

    i_lat, i_lon = divmod(id, 144)
    c_lat = -89.0 + i_lat * 2.0
    c_lon = -178.75 + i_lon * 2.5

    if not DATABASE_URL.startswith("postgres"):
        raise HTTPException(503, "DATABASE_URL tanımlı değil.")

    # Neon.tech serverless mimarisiyle %100 uyumlu, kopma yapmayan doğrudan bağlantı
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT katman_kodu, cozunurluk, degerler FROM kuresel_katmanlar WHERE nokta_id = %s;",
                    (id,)
                )
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(500, f"Veritabanı bağlantı hatası: {e}")

    seriler = {
        kod: {"cozunurluk": coz, "adim_sayisi": len(deg), "degerler": deg}
        for kod, coz, deg in rows
    }
    return {"nokta_id": id, "lat": c_lat, "lon": c_lon, "seriler": seriler}
