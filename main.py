import json
import os
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="Videasy API")

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Videasy API</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-base: #030712;
                --bg-panel: #0f172a;
                --bg-card: #1e293b;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --accent-primary: #38bdf8;
                --accent-gradient: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
                --border-light: rgba(255, 255, 255, 0.08);
            }
            body { font-family: 'Inter', sans-serif; background: var(--bg-base); color: var(--text-main); margin: 0; line-height: 1.7; -webkit-font-smoothing: antialiased; }
            * { box-sizing: border-box; }
            .nav { padding: 20px 0; border-bottom: 1px solid var(--border-light); background: rgba(3,7,18,0.8); backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 50; }
            .nav-inner { max-width: 1000px; margin: 0 auto; padding: 0 32px; display: flex; align-items: center; gap: 12px; }
            .logo { height: 36px; object-fit: contain; border-radius: 4px; }
            .logo-text { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; }
            
            .hero { padding: 100px 32px 60px; text-align: center; }
            .badge { display: inline-block; background: rgba(56,189,248,0.1); color: var(--accent-primary); padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; letter-spacing: 0.05em; padding-bottom: 7px; margin-bottom: 24px; border: 1px solid rgba(56,189,248,0.2); }
            h1 { font-size: 4.5rem; font-weight: 800; letter-spacing: -0.04em; margin: 0 0 24px 0; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.1; }
            .hero p { font-size: 1.25rem; color: var(--text-muted); max-width: 600px; margin: 0 auto; }
            
            .container { max-width: 1000px; margin: 0 auto; padding: 40px 32px 100px; }
            h2 { font-size: 1.8rem; font-weight: 600; margin: 60px 0 24px 0; letter-spacing: -0.02em; display: flex; align-items: center; gap: 16px; }
            h2::after { content: ''; flex: 1; height: 1px; background: var(--border-light); }
            
            .step-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }
            .step { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; padding: 32px; transition: transform 0.2s ease, box-shadow 0.2s ease; position: relative; overflow: hidden; }
            .step:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.4); border-color: rgba(56,189,248,0.3); }
            .step::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: var(--accent-gradient); opacity: 0; transition: opacity 0.2s; }
            .step:hover::before { opacity: 1; }
            .step-num { width: 40px; height: 40px; border-radius: 50%; background: rgba(56,189,248,0.1); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; margin-bottom: 24px; border: 1px solid rgba(56,189,248,0.2); }
            .step h3 { margin: 0 0 12px 0; font-size: 1.25rem; }
            .step p { color: var(--text-muted); font-size: 0.95rem; margin: 0; }
            
            .endpoint-wrapper { background: var(--bg-panel); border: 1px solid var(--border-light); border-radius: 16px; overflow: hidden; margin-top: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            .endpoint-head { padding: 20px 24px; border-bottom: 1px solid var(--border-light); display: flex; align-items: center; gap: 16px; background: rgba(255,255,255,0.02); }
            .method-get { background: rgba(16,185,129,0.15); color: #34d399; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; letter-spacing: 0.05em; border: 1px solid rgba(16,185,129,0.2); }
            .endpoint-url { font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; color: #e2e8f0; }
            
            .table-wrap { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; background: var(--bg-panel); }
            th, td { padding: 18px 24px; text-align: left; border-bottom: 1px solid var(--border-light); }
            th { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); font-weight: 600; background: rgba(255,255,255,0.02); }
            td { font-size: 0.95rem; }
            tr:last-child td { border-bottom: none; }
            
            code { font-family: 'JetBrains Mono', monospace; background: rgba(255,255,255,0.06); padding: 4px 8px; border-radius: 6px; font-size: 0.9em; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.05); }
            .type-str { color: #fca5a5; font-size: 0.85em; font-family: 'JetBrains Mono', monospace; background: rgba(252,165,165,0.1); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(252,165,165,0.2); }
            .type-int { color: #93c5fd; font-size: 0.85em; font-family: 'JetBrains Mono', monospace; background: rgba(147,197,253,0.1); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(147,197,253,0.2); }
            
            .examples { display: grid; gap: 16px; margin-top: 32px; }
            .example-card { display: flex; align-items: stretch; background: var(--bg-card); border: 1px solid var(--border-light); padding: 24px 32px; border-radius: 16px; color: var(--text-main); }
            .example-card .icon { font-size: 2rem; margin-right: 24px; padding-top: 4px; }
            .example-content { flex: 1; overflow: hidden; }
            .example-content h4 { margin: 0 0 8px 0; font-size: 1.15rem; font-weight: 600; display: flex; align-items: center; gap: 10px; }
            .example-content p { margin: 0; color: var(--text-muted); font-size: 0.95rem; }
            .pill { font-size: 0.75rem; background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 20px; font-weight: 600; letter-spacing: 0.05em; color: #cbd5e1; }
            
            .footer { text-align: center; padding: 48px 32px; border-top: 1px solid var(--border-light); color: var(--text-muted); font-size: 0.95rem; font-weight: 500; letter-spacing: 0.02em; margin-top: 40px; }
            .footer span { color: var(--accent-primary); }
        </style>
    </head>
    <body>
        <nav class="nav">
            <div class="nav-inner">
                <img src="https://www.videasy.net/logo.png" class="logo" alt="Videasy Logo">
                <div class="logo-text">Videasy API</div>
            </div>
        </nav>
        
        <div class="hero">
            <div class="badge">V1.0 NATIVE DECRYPTION ENGINE</div>
            <h1>The fastest stream unlocker.</h1>
            <p>A completely headless backend utilizing pure WebAssembly mapped directly onto a virtualized Node.js environment to effortlessly bypass stream obfuscation.</p>
        </div>

        <div class="container">
            <h2>The Pipeline</h2>
            <div class="step-grid">
                <div class="step">
                    <div class="step-num">1</div>
                    <h3>Locate Media</h3>
                    <p>Search for any Movie or TV Show using the official <strong>TMDB API</strong> or directly on <code>themoviedb.org</code> homepage.</p>
                </div>
                <div class="step">
                    <div class="step-num">2</div>
                    <h3>Extract ID</h3>
                    <p>Grab the <code>tmdbId</code> from the search payload. (e.g. <code>157336</code> for Interstellar).</p>
                </div>
                <div class="step">
                    <div class="step-num">3</div>
                    <h3>Decrypt Stream</h3>
                    <p>Pass the ID into the <code>/sources</code> endpoint. The WASM execution instantly strips the padding and unlocks the 1080p M3U8 arrays.</p>
                </div>
            </div>

            <h2>Endpoint Reference</h2>
            <div class="endpoint-wrapper">
                <div class="endpoint-head">
                    <span class="method-get">GET</span>
                    <span class="endpoint-url">/sources</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <tr><th>Parameter</th><th>Type</th><th>Description</th></tr>
                        <tr><td><code>title</code></td><td><span class="type-str">string</span></td><td>Name of the media (for internal routing logging)</td></tr>
                        <tr><td><code>mediaType</code></td><td><span class="type-str">string</span></td><td>Must be exactly <code>movie</code> or <code>tv</code></td></tr>
                        <tr><td><code>tmdbId</code></td><td><span class="type-int">int</span></td><td>The official TMDB numerical ID</td></tr>
                        <tr><td><code>year</code></td><td><span class="type-int">int</span></td><td>Release year (Optional: pass empty string if unknown)</td></tr>
                        <tr><td><code>seasonId</code></td><td><span class="type-int">int</span></td><td>Sequence number. Required for TV shows. (Default: <code>1</code>)</td></tr>
                        <tr><td><code>episodeId</code></td><td><span class="type-int">int</span></td><td>Sequence number. Required for TV shows. (Default: <code>1</code>)</td></tr>
                        <tr><td><code>imdbId</code></td><td><span class="type-str">string</span></td><td>The IMDB ID (Optional: pass empty string if unknown)</td></tr>
                    </table>
                </div>
            </div>

            <h2>Live Playgrounds</h2>
            <p style="color: var(--text-muted); margin-bottom: 24px;">Click any card to instantly open the raw decrypted JSON stream array in a new tab.</p>
            
            <div class="examples">
                <div class="example-card">
                    <div class="icon">🎬</div>
                    <div class="example-content">
                        <h4>Interstellar <span class="pill">MOVIE</span></h4>
                        <p><strong>TMDB ID:</strong> 157336</p>
                        <code style="display: block; margin: 12px 0; padding: 10px; font-size: 0.8rem; overflow-x: auto; white-space: nowrap;">/sources?title=Interstellar&mediaType=movie&year=2014&tmdbId=157336</code>
                        <a href="/sources?title=Interstellar&mediaType=movie&year=2014&tmdbId=157336" target="_blank" style="font-size: 0.9rem; font-weight: 600;">Test Endpoint &rarr;</a>
                    </div>
                </div>

                <div class="example-card">
                    <div class="icon">📺</div>
                    <div class="example-content">
                        <h4>Breaking Bad <span class="pill">TV SHOW | S1E1</span></h4>
                        <p><strong>TMDB ID:</strong> 1396</p>
                        <code style="display: block; margin: 12px 0; padding: 10px; font-size: 0.8rem; overflow-x: auto; white-space: nowrap;">/sources?title=Breaking+Bad&mediaType=tv&year=2008&seasonId=1&episodeId=1&tmdbId=1396</code>
                        <a href="/sources?title=Breaking+Bad&mediaType=tv&year=2008&seasonId=1&episodeId=1&tmdbId=1396" target="_blank" style="font-size: 0.9rem; font-weight: 600;">Test Endpoint &rarr;</a>
                    </div>
                </div>

                <div class="example-card">
                    <div class="icon">👽</div>
                    <div class="example-content">
                        <h4>Stranger Things <span class="pill">TV SHOW | S1E1</span></h4>
                        <p><strong>TMDB ID:</strong> 66732</p>
                        <code style="display: block; margin: 12px 0; padding: 10px; font-size: 0.8rem; overflow-x: auto; white-space: nowrap;">/sources?title=Stranger+Things&mediaType=tv&year=2016&seasonId=1&episodeId=1&tmdbId=66732</code>
                        <a href="/sources?title=Stranger+Things&mediaType=tv&year=2016&seasonId=1&episodeId=1&tmdbId=66732" target="_blank" style="font-size: 0.9rem; font-weight: 600;">Test Endpoint &rarr;</a>
                    </div>
                </div>
            </div>
            
        </div>

        <div class="footer">
            Developer : <span>Walter</span>
        </div>
    </body>
    </html>
    """

@app.get("/sources")
def get_sources(
    title: str = Query(...),
    mediaType: str = Query(...),
    tmdbId: str = Query(...),
    provider: str = Query(default="myflixerzupcloud"),
    year: str = Query(default=""),
    episodeId: str = Query(default="1"),
    seasonId: str = Query(default="1"),
    imdbId: str = Query(default="")
) -> dict[str, Any]:
    query_params = {
        "title": title,
        "mediaType": mediaType,
        "year": year,
        "episodeId": episodeId,
        "seasonId": seasonId,
        "tmdbId": tmdbId,
        "imdbId": imdbId
    }
    url = f"https://api.videasy.net/{provider}/sources-with-title?{urlencode(query_params)}"
    
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Referer": "https://cineby.sc/",
        "Origin": "https://cineby.sc",
    })
    
    try:
        with urlopen(req, timeout=20) as r:
            ct_hex = r.read().decode("utf-8", errors="replace").strip()
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Videasy sources HTTP error: {exc.code}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Videasy sources connection error: {exc.reason}") from exc
        
    if not ct_hex:
        raise HTTPException(status_code=404, detail="No sources found or empty ciphertext returned")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        result = subprocess.run(
            ["node", "decrypt.js", ct_hex, str(tmdbId)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=script_dir,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Node decryption failed: {result.stderr}")
            
        out = json.loads(result.stdout)
        if not out.get("success"):
            raise HTTPException(status_code=500, detail=f"Decryption logic error: {out.get('error')}")
            
        return {
            "source": url,
            "provider": provider,
            "data": out["data"]
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Node.js decryption timed out")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse Node.js decryption output")
