"""Runs one SDK's dump program through every download/cache scenario against a fake bundles server.

    python3 suite.py <lang> -- <command...>

The command is run as `<command...> <baseUrl> <cacheDir> <token|-> <cache 1|0> [platform [instance]]`, must print the
dump (see README.md) on success, or `{"error": {"status": <int|null>}}` and exit 3 on AWSPricingDataError.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

here = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(here, "fixture")
NAME = open(os.path.join(FIX, "latest")).read().strip()
REFERENCE = json.load(open(os.path.join(here, "reference.json"), encoding="utf-8"))
REFERENCE_RDS = json.load(open(os.path.join(here, "reference-rds.json"), encoding="utf-8"))

lang = sys.argv[1]
cmd = sys.argv[sys.argv.index("--") + 1:]

class State:
    fail_latest = 0      # answer this many /latest requests with 503
    latest_body = None   # override /latest content
    fail_api = 0         # answer this many API requests with 503
    log = []             # (path, auth, user-agent)

API = "/api/v1/aws-bulk-pricing/"

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
        if self.path.startswith(API):
            if State.fail_api > 0:
                State.fail_api -= 1
                return self.reply(503, b"busy", {"Retry-After": "1"})
            platform, _, name = self.path[len(API):].partition("/")
            p = os.path.join(FIX, "api", platform, urllib.parse.unquote(name) + ".json")
            if "/" not in urllib.parse.unquote(name) and os.path.isfile(p):
                return self.reply(200, open(p, "rb").read(), {"Content-Type": "application/json"})
            return self.reply(404, b'{"error":"No such instance"}', {"Content-Type": "application/json"})
        if self.path == "/rds-latest":
            return self.reply(200, open(os.path.join(FIX, "rds-latest"), "rb").read())
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

def run(base, cache_dir, token="test-token", cache=True, env_token=None, platform=None, instance=None):
    env = {k: v for k, v in os.environ.items() if k != "INFRAWRENCH_API_KEY"}
    if env_token: env["INFRAWRENCH_API_KEY"] = env_token
    State.log = []
    t = time.time()
    args = [base, cache_dir, token, "1" if cache else "0"] + ([platform] if platform else []) + ([instance] if instance is not None else [])
    p = subprocess.run(cmd + args, capture_output=True, text=True, env=env, encoding="utf-8")
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

def dump_ok(name, p, out, reference=REFERENCE):
    d = diff(out, reference) if out is not None else f"exit {p.returncode}, stdout={p.stdout[:300]!r}, stderr={p.stderr[-1500:]!r}"
    check(name, d is None, d)

def error_with(name, p, out, status):
    ok = p.returncode == 3 and isinstance(out, dict) and "error" in out and out["error"].get("status") == status
    check(name, ok, f"exit {p.returncode}, stdout={p.stdout[:300]!r}, stderr={p.stderr[-800:]!r}")

tmp = tempfile.mkdtemp()
try:
    cache = os.path.join(tmp, "cache")
    os.makedirs(cache)
    for f in ["bundle-20200101T000000Z.json", "bundle-20200101T000000Z.json.xz", "keep.txt", "rds-bundle-20200101T000000Z.json"]:
        open(os.path.join(cache, f), "w").write("{}")

    p, out, _ = run(BASE, cache)
    dump_ok("fresh download decodes to the reference", p, out)
    check("cache holds the new bundle, old bundles deleted, other files and platforms kept",
          sorted(os.listdir(cache)) == sorted([f"bundle-{NAME}.json", "keep.txt", "rds-bundle-20200101T000000Z.json"]), sorted(os.listdir(cache)))
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

    # Other platforms: rds-latest names rds-bundle-<NAME>.json.xz, cached beside EC2's bundle.
    p, out, _ = run(BASE, cache, platform="rds")
    dump_ok("rds download decodes to the rds reference", p, out, REFERENCE_RDS)
    check("rds fetches rds-latest and its bundle", [x[0] for x in State.log] == ["/rds-latest", f"/rds-bundle-{NAME}.json.xz"], State.log)
    check("rds replaces only its own old bundle, keeping EC2's",
          sorted(os.listdir(cache)) == sorted([f"bundle-{NAME}.json", "keep.txt", f"rds-bundle-{NAME}.json"]), sorted(os.listdir(cache)))
    p, out, _ = run(BASE, cache, platform="rds")
    dump_ok("rds cached load decodes to the rds reference", p, out, REFERENCE_RDS)
    check("rds cached load only fetches rds-latest", [x[0] for x in State.log] == ["/rds-latest"], State.log)
    p, out, _ = run(DEAD, cache, platform="rds")
    dump_ok("rds offline falls back to the rds cache", p, out, REFERENCE_RDS)
    p, out, _ = run(BASE, cache, platform="ec2")
    dump_ok("platform ec2 is the EC2 bundle", p, out)
    check("platform ec2 fetches latest", [x[0] for x in State.log] == ["/latest"], State.log)

    ec2_only = os.path.join(tmp, "ec2only")
    os.makedirs(ec2_only)
    shutil.copy(os.path.join(cache, f"bundle-{NAME}.json"), ec2_only)
    p, out, _ = run(DEAD, ec2_only, platform="rds")
    check("rds offline never falls back to another platform's bundle", p.returncode != 0, p.stdout[:200])
    p, out, _ = run(BASE, os.path.join(tmp, "unknown"), platform="nope")
    error_with("a platform with no bundle is a 404", p, out, 404)
    p, out, _ = run(BASE, os.path.join(tmp, "badname"), platform="../rds")
    error_with("a malformed platform name is an AWSPricingDataError", p, out, None)
    check("a malformed platform name makes no request", State.log == [], State.log)

    # One instance from the Infrawrench API, decoded the same as from the whole bundle. attributesIn is
    # dumped for the regions the instance's attributes are overridden in; any other gives `attributes`.
    unused = os.path.join(tmp, "unused")
    for platform, reference in [("ec2", REFERENCE), ("rds", REFERENCE_RDS)]:
        for name, expected in reference["instances"].items():
            p, out, _ = run(BASE, unused, platform=platform, instance=name)
            got = out.get("instance") if isinstance(out, dict) else None
            if isinstance(got, dict) and isinstance(got.get("attributesIn"), dict):
                expected = {**expected, "attributesIn": {r: expected["attributesIn"].get(r) for r in got["attributesIn"]}}
            dump_ok(f"API {platform}/{name} decodes to the reference", p, got, expected)
            check(f"API {platform}/{name} fetches only that instance",
                  [x[:2] for x in State.log] == [(f"{API}{platform}/{name}", "Bearer test-token")], State.log)
    check("API User-Agent", {ua for _, _, ua in State.log} == {f"infrawrench/bulk-instances, {lang}, 1.0"}, State.log)

    p, out, _ = run(BASE, unused, platform="ec2", instance="nope")
    check("API missing instance is null", p.returncode == 0 and out == {"instance": None}, (p.returncode, p.stdout[:200], p.stderr[-800:]))
    p, out, _ = run(BASE + "/", unused, platform="ec2", instance="x y/z")
    check("API escapes the instance type, and drops a trailing slash from the base URL",
          out == {"instance": None} and [x[0] for x in State.log] == [f"{API}ec2/x%20y%2Fz"], (p.stdout[:200], State.log))
    p, out, _ = run(BASE, unused, token="wrong", platform="ec2", instance="m5.large")
    error_with("API rejected token is 401", p, out, 401)
    State.fail_api = 1
    p, out, secs = run(BASE, unused, platform="ec2", instance="m5.large")
    check("API 503 is retried", isinstance(out, dict) and out.get("instance") is not None and secs >= 1
          and len(State.log) == 2, (secs, p.stdout[:200], State.log))
    State.fail_api = 3
    p, out, _ = run(BASE, unused, platform="ec2", instance="m5.large")
    error_with("API three 503s give up with status 503", p, out, 503)
    State.fail_api = 0
    p, out, _ = run(BASE, unused, token="-", env_token="test-token", platform="rds", instance="db.t3.micro")
    check("API token defaults to INFRAWRENCH_API_KEY", isinstance(out, dict) and out.get("instance") is not None, p.stdout[:200])
    p, out, _ = run(BASE, unused, token="-", platform="rds", instance="db.t3.micro")
    error_with("API no token at all is an AWSPricingDataError", p, out, None)
    p, out, _ = run(BASE, unused, platform="../ec2", instance="m5.large")
    error_with("API malformed platform name is an AWSPricingDataError", p, out, None)
    check("API malformed platform name makes no request", State.log == [], State.log)
    p, out, _ = run(BASE, unused, platform="ec2", instance="")
    error_with("API empty instance type is an AWSPricingDataError", p, out, None)
    check("API empty instance type makes no request", State.log == [], State.log)
    p, out, _ = run(DEAD, unused, platform="ec2", instance="m5.large")
    check("API offline fails", p.returncode != 0, p.stdout[:200])
    check("API writes nothing to the cache directory", not os.path.exists(unused), unused)
finally:
    shutil.rmtree(tmp)
    server.shutdown()

print(f"\n{lang}: {'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
sys.exit(1 if failures else 0)
