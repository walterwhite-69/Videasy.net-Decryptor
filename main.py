import json
import os
import subprocess
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

API_BASE = "https://api.videasy.to"
ORIGIN   = "https://www.vidking.net"
REFERER  = "https://www.vidking.net/"

PROVIDERS = [
    {"name": "Oxygen",   "endpoint": "mb-flix",    "active": True},
    {"name": "Hydrogen", "endpoint": "cdn",         "active": True},
    {"name": "Lithium",  "endpoint": "downloader2", "active": True},
    {"name": "Helium",   "endpoint": "1movies",     "active": False},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Referer": REFERER,
    "Origin":  ORIGIN,
}

app = FastAPI(title="Videasy API")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _fetch_cipher(provider_endpoint: str, params: dict) -> str:
    url = f"{API_BASE}/{provider_endpoint}/sources-with-title?{urlencode(params)}"
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace").strip()


def _node_decrypt(cipher_hex: str, tmdb_id: str) -> dict:
    # Write the ciphertext to a temp file instead of passing it as a CLI
    # argument — Windows caps command-line length and large payloads
    # (now ~50KB+ per the new API) will exceed it (WinError 206).
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(cipher_hex)
            tmp_path = f.name

        result = subprocess.run(
            ["node", "--max-old-space-size=4096", "decrypt.js", tmp_path, tmdb_id],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=SCRIPT_DIR,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node exited {result.returncode}: {result.stderr.strip()}")
        out = json.loads(result.stdout)
        if not out.get("success"):
            raise RuntimeError(out.get("error", "unknown decryption error"))
        return out["data"]
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _get_sources(query_params: dict, provider_name: str | None = None) -> dict:
    active = [p for p in PROVIDERS if p["active"]]
    if provider_name:
        active = [p for p in active if p["name"].lower() == provider_name.lower()]
        if not active:
            raise HTTPException(status_code=400, detail=f"Unknown or inactive provider: {provider_name}")

    errors = []
    for p in active:
        try:
            cipher = _fetch_cipher(p["endpoint"], query_params)
            if not cipher:
                errors.append(f"{p['name']}: empty response")
                continue
            data = _node_decrypt(cipher, query_params["tmdbId"])
            return {"provider": p["name"], "data": data}
        except HTTPError as e:
            errors.append(f"{p['name']}: HTTP {e.code}")
        except URLError as e:
            errors.append(f"{p['name']}: connection error — {e.reason}")
        except subprocess.TimeoutExpired:
            errors.append(f"{p['name']}: decrypt timed out")
        except (RuntimeError, json.JSONDecodeError, ValueError, TypeError) as e:
            errors.append(f"{p['name']}: {e}")

    raise HTTPException(
        status_code=502,
        detail=f"All providers failed — {'; '.join(errors)}",
    )


def _provider_links(base_qs: str) -> str:
    active = [p for p in PROVIDERS if p["active"]]
    return " ".join(
        f'<a href="/sources?{base_qs}&provider={p["name"]}" target="_blank">{p["name"]} ↗</a>'
        for p in active
    )


@app.get("/", response_class=HTMLResponse)
def root():
    active_providers = [p for p in PROVIDERS if p["active"]]
    provider_rows = "".join(
        f'<tr><td><code>{p["name"]}</code></td>'
        f'<td><span class="badge-green">Active</span></td>'
        f'<td><code>{p["endpoint"]}</code></td></tr>'
        for p in active_providers
    )

    ex_movie  = "title=Interstellar&mediaType=movie&year=2014&tmdbId=157336"
    ex_bb     = "title=Breaking+Bad&mediaType=tv&year=2008&seasonId=1&episodeId=1&tmdbId=1396"
    ex_st     = "title=Stranger+Things&mediaType=tv&year=2016&seasonId=1&episodeId=1&tmdbId=66732"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Videasy Decryptor API</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #030712; --panel: #0f172a; --card: #1e293b;
      --text: #f8fafc; --muted: #94a3b8;
      --accent: #38bdf8; --grad: linear-gradient(135deg,#0ea5e9,#6366f1);
      --border: rgba(255,255,255,0.08);
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased}}
    .nav{{padding:18px 32px;border-bottom:1px solid var(--border);background:rgba(3,7,18,.85);backdrop-filter:blur(12px);position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:12px}}
    .logo-text{{font-size:1.2rem;font-weight:700;letter-spacing:-.02em}}
    .hero{{padding:90px 32px 50px;text-align:center}}
    .badge{{display:inline-block;background:rgba(56,189,248,.1);color:var(--accent);padding:5px 14px;border-radius:20px;font-size:.82rem;font-weight:600;letter-spacing:.05em;border:1px solid rgba(56,189,248,.2);margin-bottom:22px}}
    h1{{font-size:clamp(2.5rem,6vw,4rem);font-weight:800;letter-spacing:-.04em;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.1;margin-bottom:18px}}
    .hero p{{font-size:1.15rem;color:var(--muted);max-width:580px;margin:0 auto}}
    .container{{max-width:960px;margin:0 auto;padding:20px 32px 80px}}
    h2{{font-size:1.6rem;font-weight:600;margin:50px 0 20px;letter-spacing:-.02em;display:flex;align-items:center;gap:14px}}
    h2::after{{content:'';flex:1;height:1px;background:var(--border)}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:28px;transition:.2s}}
    .card:hover{{transform:translateY(-3px);box-shadow:0 16px 36px rgba(0,0,0,.35);border-color:rgba(56,189,248,.25)}}
    .card-num{{width:36px;height:36px;border-radius:50%;background:rgba(56,189,248,.1);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;margin-bottom:18px;border:1px solid rgba(56,189,248,.2)}}
    .card h3{{margin-bottom:8px;font-size:1.1rem}}
    .card p{{color:var(--muted);font-size:.9rem}}
    .endpoint-box{{background:var(--panel);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-top:24px}}
    .ep-head{{padding:16px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px}}
    .get{{background:rgba(16,185,129,.15);color:#34d399;padding:4px 12px;border-radius:7px;font-weight:700;font-size:.85rem;border:1px solid rgba(16,185,129,.2)}}
    .ep-url{{font-family:'JetBrains Mono',monospace;font-size:1rem;color:#e2e8f0}}
    table{{width:100%;border-collapse:collapse}}
    th,td{{padding:14px 22px;text-align:left;border-bottom:1px solid var(--border)}}
    th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:600;background:rgba(255,255,255,.02)}}
    tr:last-child td{{border-bottom:none}}
    code{{font-family:'JetBrains Mono',monospace;background:rgba(255,255,255,.06);padding:3px 7px;border-radius:5px;font-size:.88em;border:1px solid rgba(255,255,255,.05)}}
    .type-s{{color:#fca5a5;font-size:.8em;font-family:'JetBrains Mono',monospace;background:rgba(252,165,165,.1);padding:2px 7px;border-radius:4px;border:1px solid rgba(252,165,165,.2)}}
    .type-i{{color:#93c5fd;font-size:.8em;font-family:'JetBrains Mono',monospace;background:rgba(147,197,253,.1);padding:2px 7px;border-radius:4px;border:1px solid rgba(147,197,253,.2)}}
    .badge-green{{background:rgba(16,185,129,.15);color:#34d399;padding:2px 8px;border-radius:5px;font-size:.8em;font-weight:600;border:1px solid rgba(16,185,129,.2)}}
    .examples{{display:grid;gap:14px;margin-top:24px}}
    .ex{{display:flex;align-items:flex-start;background:var(--card);border:1px solid var(--border);padding:20px 26px;border-radius:14px}}
    .ex .icon{{font-size:1.8rem;margin-right:20px;padding-top:2px}}
    .ex h4{{margin-bottom:6px;font-size:1.05rem;font-weight:600}}
    .ex p{{color:var(--muted);font-size:.9rem;margin:0}}
    .ex code{{display:block;margin:10px 0;padding:8px;font-size:.77rem;overflow-x:auto;white-space:nowrap}}
    .ex-links{{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}}
    .ex-links a{{font-size:.84rem;font-weight:600;color:var(--accent);text-decoration:none;background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.2);padding:4px 12px;border-radius:7px;transition:.15s}}
    .ex-links a:hover{{background:rgba(56,189,248,.18)}}
    .footer{{text-align:center;padding:40px 32px;border-top:1px solid var(--border);color:var(--muted);font-size:.9rem;margin-top:30px}}
    .footer span{{color:var(--accent)}}
  </style>
</head>
<body>
  <nav class="nav">
    <img src="https://www.vidking.net/assets/icon/favicon-32x32.png" style="height:28px;border-radius:4px" alt="">
    <div class="logo-text">Videasy Decryptor API</div>
  </nav>

  <div class="hero">
    <div class="badge">V2.0 · MULTI-PROVIDER · NATIVE PIPELINE</div>
    <h1>Stream Unlocker</h1>
    <p>Headless decryption engine — multi-provider fallback, future-proof PoW patch, native key derivation.</p>
  </div>

  <div class="container">
    <h2>Pipeline</h2>
    <div class="grid">
      <div class="card"><div class="card-num">1</div><h3>Find Media</h3><p>Get the <strong>TMDB ID</strong> from themoviedb.org for any movie or TV show.</p></div>
      <div class="card"><div class="card-num">2</div><h3>Hit /sources</h3><p>Pass the ID to the endpoint. All active providers are tried automatically — first success wins.</p></div>
      <div class="card"><div class="card-num">3</div><h3>Get Streams</h3><p>Receive clean JSON with quality-labelled <code>.m3u8</code> URLs and subtitle tracks.</p></div>
    </div>

    <h2>Endpoint</h2>
    <div class="endpoint-box">
      <div class="ep-head"><span class="get">GET</span><span class="ep-url">/sources</span></div>
      <table>
        <tr><th>Parameter</th><th>Type</th><th>Description</th></tr>
        <tr><td><code>tmdbId</code></td><td><span class="type-i">int</span></td><td>TMDB numerical ID <strong>(required)</strong></td></tr>
        <tr><td><code>mediaType</code></td><td><span class="type-s">string</span></td><td><code>movie</code> or <code>tv</code> <strong>(required)</strong></td></tr>
        <tr><td><code>title</code></td><td><span class="type-s">string</span></td><td>Media title (required)</td></tr>
        <tr><td><code>year</code></td><td><span class="type-i">int</span></td><td>Release year (optional)</td></tr>
        <tr><td><code>seasonId</code></td><td><span class="type-i">int</span></td><td>Season number — TV only (default: 1)</td></tr>
        <tr><td><code>episodeId</code></td><td><span class="type-i">int</span></td><td>Episode number — TV only (default: 1)</td></tr>
        <tr><td><code>imdbId</code></td><td><span class="type-s">string</span></td><td>IMDB ID (optional)</td></tr>
        <tr><td><code>provider</code></td><td><span class="type-s">string</span></td><td>Force a specific provider — <code>Oxygen</code>, <code>Hydrogen</code>, <code>Lithium</code> (optional)</td></tr>
      </table>
    </div>

    <h2>Providers</h2>
    <div class="endpoint-box">
      <table>
        <tr><th>Name</th><th>Status</th><th>Endpoint</th></tr>
        {provider_rows}
      </table>
    </div>

    <h2>Examples</h2>
    <div class="examples">
      <div class="ex">
        <div class="icon">🎬</div>
        <div style="width:100%">
          <h4>Interstellar <span style="font-size:.75rem;background:rgba(255,255,255,.08);padding:2px 7px;border-radius:12px;font-weight:600">MOVIE</span></h4>
          <p>TMDB ID: 157336</p>
          <code>/sources?{ex_movie}&amp;provider=Oxygen</code>
          <div class="ex-links">{_provider_links(ex_movie)}</div>
        </div>
      </div>
      <div class="ex">
        <div class="icon">📺</div>
        <div style="width:100%">
          <h4>Breaking Bad <span style="font-size:.75rem;background:rgba(255,255,255,.08);padding:2px 7px;border-radius:12px;font-weight:600">TV · S1E1</span></h4>
          <p>TMDB ID: 1396</p>
          <code>/sources?{ex_bb}&amp;provider=Oxygen</code>
          <div class="ex-links">{_provider_links(ex_bb)}</div>
        </div>
      </div>
      <div class="ex">
        <div class="icon">👽</div>
        <div style="width:100%">
          <h4>Stranger Things <span style="font-size:.75rem;background:rgba(255,255,255,.08);padding:2px 7px;border-radius:12px;font-weight:600">TV · S1E1</span></h4>
          <p>TMDB ID: 66732</p>
          <code>/sources?{ex_st}&amp;provider=Oxygen</code>
          <div class="ex-links">{_provider_links(ex_st)}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">Developer: <span>Walter</span></div>
</body>
</html>"""


@app.get("/sources")
def get_sources(
    title:     str = Query(...),
    mediaType: str = Query(...),
    tmdbId:    str = Query(...),
    provider:  str = Query(default=""),
    year:      str = Query(default=""),
    episodeId: str = Query(default="1"),
    seasonId:  str = Query(default="1"),
    imdbId:    str = Query(default=""),
):
    query_params = {
        "title":     title,
        "mediaType": mediaType,
        "year":      year,
        "episodeId": episodeId,
        "seasonId":  seasonId,
        "tmdbId":    tmdbId,
        "imdbId":    imdbId,
    }
    result = _get_sources(query_params, provider_name=provider or None)
    return {
        "tmdbId":   tmdbId,
        "provider": result["provider"],
        "data":     result["data"],
    }


@app.get("/providers")
def list_providers():
    return {
        "providers": [
            {"name": p["name"], "endpoint": p["endpoint"], "active": p["active"]}
            for p in PROVIDERS
        ]
    }