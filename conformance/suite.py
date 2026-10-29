"""Runs one SDK's dump program through every download/cache scenario against a fake bundles server.

    python3 suite.py <lang> -- <command...>

The command is run as `<command...> <baseUrl> <cacheDir> <token|-> <cache 1|0>`, must print the dump
(see README.md) on success, or `{"error": {"status": <int|null>}}` and exit 3 on AWSPricingDataError.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

here = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(here, "fixture")
NAME = open(os.path.join(FIX, "latest")).read().strip()
REFERENCE = json.load(open(os.path.join(here, "reference.json"), encoding="utf-8"))

lang = sys.argv[1]
cmd = sys.argv[sys.argv.index("--") + 1:]

class State:
    fail_latest = 0      # answer this many /latest requests with 503
    latest_body = None   # override /latest content
    log = []             # (path, auth, user-agent)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        State.log.append((self.path, self.headers.get("Authorization"), self.headers.get("User-Agent")))
        if self.headers.get("Authorization") != "Bearer test-token":
            return self.reply(401, b"unauthorized")
        if self.path == "/latest":
            if State.fail_latest > 0:
                State.fail_latest -= 1
                return self.reply(503, b"busy", {"Retry-After": "1"})
            body = State.latest_body if State.latest_body is not None else open(os.path.join(FIX, "latest"), "rb").read()
            return self.reply(200, body)
        p = os.path.join(FIX, self.path.lstrip("/"))
        if self.path.endswith(".json.xz") and os.path.isfile(p):
            return self.reply(200, open(p, "rb").read())
        self.reply(404, b"not found")
    def reply(self, code, body, headers={}):
        self.send_response(code)
        for k, v in headers.items(): self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{server.server_address[1]}"
DEAD = "http://127.0.0.1:9"

def run(base, cache_dir, token="test-token", cache=True, env_token=None):
    env = {k: v for k, v in os.environ.items() if k != "INFRAWRENCH_API_KEY"}
    if env_token: env["INFRAWRENCH_API_KEY"] = env_token
    State.log = []
    t = time.time()
    p = subprocess.run(cmd + [base, cache_dir, token, "1" if cache else "0"], capture_output=True, text=True, env=env, encoding="utf-8")
    try:
        out = json.loads(p.stdout)
    except Exception:
        out = None
    return p, out, time.time() - t

failures = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -- {detail}"))
    if not cond: failures.append(name)

def diff(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: return f"{path}.{k}: missing on one side ({'got' if k in a else 'expected'} has it)"
            d = diff(a[k], b[k], f"{path}.{k}")
            if d: return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff(x, y, f"{path}[{i}]")
            if d: return d
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a is b else f"{path}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return None if abs(a - b) < 1e-12 else f"{path}: {a!r} != {b!r}"
    return None if a == b else f"{path}: {a!r} != {b!r}"

def dump_ok(name, p, out):
    d = diff(out, REFERENCE) if out is not None else f"exit {p.returncode}, stdout={p.stdout[:300]!r}, stderr={p.stderr[-1500:]!r}"
    check(name, d is None, d)

def error_with(name, p, out, status):
    ok = p.returncode == 3 and isinstance(out, dict) and "error" in out and out["error"].get("status") == status
    check(name, ok, f"exit {p.returncode}, stdout={p.stdout[:300]!r}, stderr={p.stderr[-800:]!r}")

tmp = tempfile.mkdtemp()
try:
    cache = os.path.join(tmp, "cache")
    os.makedirs(cache)
    for f in ["bundle-20200101T000000Z.json", "bundle-20200101T000000Z.json.xz", "keep.txt"]:
        open(os.path.join(cache, f), "w").write("{}")

    p, out, _ = run(BASE, cache)
    dump_ok("fresh download decodes to the reference", p, out)
    check("cache holds the new bundle, old bundles deleted, other files kept",
          sorted(os.listdir(cache)) == sorted([f"bundle-{NAME}.json", "keep.txt"]), sorted(os.listdir(cache)))
    check("cached file is the decompressed JSON",
          open(os.path.join(cache, f"bundle-{NAME}.json"), "rb").read() == open(os.path.join(FIX, f"bundle-{NAME}.json"), "rb").read())
    uas = {ua for _, _, ua in State.log}
    check("User-Agent", uas == {f"infrawrench/bulk-instances, {lang}, 1.0"}, uas)

    p, out, _ = run(BASE, cache)
    dump_ok("cached load decodes to the reference", p, out)
    check("cached load only fetches latest", [x[0] for x in State.log] == ["/latest"], State.log)

    p, out, _ = run(DEAD, cache)
    dump_ok("offline falls back to the cache", p, out)

    State.latest_body = b"../../etc/passwd"
    p, out, _ = run(BASE, cache)
    dump_ok("invalid latest falls back to the cache", p, out)
    p, out, _ = run(BASE, os.path.join(tmp, "empty1"))
    error_with("invalid latest without cache is an AWSPricingDataError", p, out, None)
    State.latest_body = None

    p, out, _ = run(BASE, cache, token="wrong")
    error_with("rejected token is 401 even with a cache", p, out, 401)

    State.fail_latest = 1
    p, out, secs = run(BASE, os.path.join(tmp, "retry"))
    dump_ok("503 is retried", p, out)
    check("503 retry honoured Retry-After", secs >= 1 and [x[0] for x in State.log][:2] == ["/latest", "/latest"], (secs, State.log))

    State.fail_latest = 3
    p, out, _ = run(BASE, os.path.join(tmp, "retry3"))
    error_with("three 503s give up with status 503", p, out, 503)
    check("three attempts", [x[0] for x in State.log] == ["/latest"] * 3, State.log)
    State.fail_latest = 0

    nocache = os.path.join(tmp, "nocache")
    p, out, _ = run(BASE, nocache, cache=False)
    dump_ok("cachePricingData=false works", p, out)
    check("cachePricingData=false writes nothing", not os.path.exists(nocache) or os.listdir(nocache) == [], nocache)
    p, out, _ = run(DEAD, cache, cache=False)
    check("cachePricingData=false does not fall back to the cache", p.returncode != 0, p.stdout[:200])

    p, out, _ = run(BASE, os.path.join(tmp, "env"), token="-", env_token="test-token")
    dump_ok("token defaults to INFRAWRENCH_API_KEY", p, out)
    p, out, _ = run(BASE, os.path.join(tmp, "env2"), token="-")
    error_with("no token at all is an AWSPricingDataError", p, out, None)

    p, out, _ = run(DEAD, os.path.join(tmp, "empty2"))
    check("offline without cache fails", p.returncode != 0, p.stdout[:200])
finally:
    shutil.rmtree(tmp)
    server.shutdown()

print(f"\n{lang}: {'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
sys.exit(1 if failures else 0)
