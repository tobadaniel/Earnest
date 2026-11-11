#!/usr/bin/env python3
"""Static digest deploy to Netlify (any account via NETLIFY_CREDENTIAL)."""
import hashlib, json, os, sys, time, urllib.error, urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

CREDENTIAL = os.environ.get("NETLIFY_CREDENTIAL", "custom.netlify-prod")
HOSTS = ["api.netlify.com"]
BASE = "https://api.netlify.com/api/v1"
DIST = os.environ["DIST_DIR"]
SITE_NAMES = [n for n in os.environ.get("SITE_NAMES", "earnesthq").split(",") if n]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


def _open(req, timeout=120):
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as resp:
            return resp.status, read_json_response(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try: parsed = json.loads(body)
        except json.JSONDecodeError: parsed = {"raw": body}
        return e.code, parsed


def call(method, path, payload=None, raw=None):
    data = raw
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        headers["Content-Type"] = "application/octet-stream"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    add_surrogate_to_request(req, CREDENTIAL, allowed_hosts=HOSTS)
    return _open(req)


def call_retry(method, path, payload=None, tries=3):
    last = None
    for _ in range(tries):
        try: return call(method, path, payload)
        except Exception as exc:
            last = exc; time.sleep(4)
    raise RuntimeError(f"{method} {path} failed: {last}")


def ensure_site():
    status, sites = call_retry("GET", "/sites?per_page=100")
    if status != 200: raise RuntimeError(f"list sites: {status} {sites}")
    by_name = {s.get("name"): s for s in sites}
    for name in SITE_NAMES:
        if name in by_name:
            s = by_name[name]
            return s["id"], s.get("ssl_url"), False
    for name in SITE_NAMES:
        status, out = call_retry("POST", "/sites", {"name": name})
        if status in (200, 201): return out["id"], out.get("ssl_url"), True
        if status == 422: continue
        raise RuntimeError(f"create {name}: {status} {out}")
    raise RuntimeError("all site names taken")


def collect(root):
    out = {}
    for dirpath, _d, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            raw = open(full, "rb").read()
            out["/" + rel] = (hashlib.sha1(raw).hexdigest(), raw)
    return out


def main():
    site_id, ssl_url, created = ensure_site()
    print("site:", site_id, ssl_url, "created:", created)
    files = collect(DIST)
    digests = {p: sha for p, (sha, _r) in files.items()}
    status, dep = call_retry("POST", f"/sites/{site_id}/deploys", {"files": digests, "async": False})
    if status not in (200, 201): raise RuntimeError(f"deploy create: {status} {dep}")
    dep_id = dep["id"]
    by_sha = {sha: (p, raw) for p, (sha, raw) in files.items()}
    for sha in dep.get("required") or []:
        p, raw = by_sha[sha]
        s, _r = call("PUT", f"/deploys/{dep_id}/files{p}", raw=raw)
        print("upload", p, s)
        if s not in (200, 201): raise RuntimeError(f"upload {p}: {s}")
    state = dep.get("state"); final = dep
    deadline = time.time() + 300
    while state not in ("ready", "error") and time.time() < deadline:
        time.sleep(4)
        _s, final = call_retry("GET", f"/deploys/{dep_id}")
        state = final.get("state")
    print("deploy state:", state, final.get("ssl_url") or ssl_url)
    s, out = call_retry("PUT", f"/sites/{site_id}", {"sso_login": False})
    print("sso lift:", s, out.get("sso_login") if isinstance(out, dict) else out)
    print("URL:", final.get("ssl_url") or ssl_url)


if __name__ == "__main__":
    main()
