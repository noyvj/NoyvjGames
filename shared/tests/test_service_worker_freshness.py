"""The service worker must never let the browser's HTTP cache answer first.

GitHub Pages sends Cache-Control: max-age=600, so without revalidation a deploy
stayed invisible for up to ten minutes even though the worker is network-first.
"""

from pathlib import Path

SW = (Path(__file__).resolve().parents[2] / "sw.js").read_text(encoding="utf-8")


def test_same_origin_requests_revalidate_with_the_server():
    assert 'fetch(request, { cache: "no-cache" })' in SW


def test_precache_skips_the_http_cache():
    assert '{ cache: "reload" }' in SW and "cache.addAll(PRECACHE_URLS)" not in SW


def test_every_precached_file_exists():
    root = Path(__file__).resolve().parents[2]
    import re
    block = SW[SW.index("const PRECACHE_URLS"):SW.index("];", SW.index("const PRECACHE_URLS"))]
    for url in re.findall(r'^\s*"([^"]+)",\s*$', block, flags=re.M):
        target = root if url == "./" else root / url.removeprefix("./")
        assert target.exists(), url
