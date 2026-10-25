#!/usr/bin/env python3
"""Walsync image client: create and edit images through https://img.walsync.com with a personal key.

  walsync_image.py setkey [--stdin]                 save your key (hidden prompt, or read from stdin); it is never printed
  walsync_image.py usage                            images used / left in the current window
  walsync_image.py generate "prompt" [options]      text -> image
  walsync_image.py edit "prompt" -i a.png [-i b.png ...] [options]   change or combine existing images (up to 16)

Options for generate/edit:
  -m, --model   flare (default, fast) | sunburst (slower, more precise) | gpt-image-2 | any id from `models`
  -q, --quality auto (default) | low | medium | high | xhigh | max     (a hint; the service may return its own)
  -a, --aspect  square (default) | landscape | portrait
  -n            images per request, 1-4 (each one counts against your quota)
  -o, --out     output file or folder (default ./walsync-images)

The key is read from $WALSYNC_IMAGE_KEY or the key file written by `setkey`. Standard library only (Python 3.8+).
Exit codes: 0 ok, 2 bad usage, 3 no key saved, 4 quota used up, 5 key rejected, 6 other failure.
"""
import argparse, base64, getpass, json, mimetypes, os, re, sys, time, uuid
import urllib.error, urllib.request

BASE_URL = os.environ.get("WALSYNC_IMAGE_URL", "https://img.walsync.com").rstrip("/")
UA = "walsync-image-skill/1.0"
MODEL_ALIASES = {"flare": "gpt-image-2.5-flare", "sunburst": "gpt-image-2.5-sunburst"}
SIZES = {"square": "1024x1024", "landscape": "1536x1024", "portrait": "1024x1536"}
QUALITIES = ("auto", "low", "medium", "high", "xhigh", "max")
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
MAX_REFS, MAX_REF_BYTES = 16, 25 * 1024 * 1024


def key_file():
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base or os.path.expanduser("~"), "walsync-image", "key")


def load_key():
    key = (os.environ.get("WALSYNC_IMAGE_KEY") or "").strip()
    if not key and os.path.exists(key_file()):
        key = open(key_file(), encoding="utf-8").read().strip()
    return key


def need_key():
    key = load_key()
    if not key:
        print("NO_KEY: no Walsync image key is saved on this machine. Ask the user for the key they were given, "
              "then run: setkey (see SKILL.md). Do not guess a key.", file=sys.stderr)
        sys.exit(3)
    return key


def call(method, path, key, body=None, content_type=None, timeout=270):
    """Return (status, json, headers). Network failures come back as status 599; GETs are retried."""
    headers = {"Authorization": "Bearer " + key, "User-Agent": UA, "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    for attempt in range(3 if method == "GET" else 1):
        req = urllib.request.Request(BASE_URL + path, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read() or b"{}"), r.headers
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw), e.headers
            except ValueError:
                return e.code, {"error": {"message": raw[:200].decode("utf-8", "replace")}}, e.headers
        except Exception as e:      # timeouts, DNS, TLS resets
            if attempt < 2 and method == "GET":
                time.sleep(2 * (attempt + 1))
                continue
            return 599, {"error": {"message": f"network problem reaching {BASE_URL}: {e}"}}, {}


def fail_for(status, data):
    msg = (data.get("error") or {}).get("message") or "request failed"
    if status == 401:
        print(f"KEY_REJECTED: the key was not accepted ({msg}). Ask the user to check or re-enter it (setkey).", file=sys.stderr)
        sys.exit(5)
    if status == 429 and (data.get("error") or {}).get("type") == "quota_exceeded":
        print(f"QUOTA_USED_UP: {msg}", file=sys.stderr)
        sys.exit(4)
    print(f"ERROR {status}: {msg}", file=sys.stderr)
    sys.exit(6)


def cmd_setkey(a):
    if a.stdin or not sys.stdin.isatty():
        key = sys.stdin.readline().strip()
    else:
        key = getpass.getpass("Paste your Walsync image key (hidden): ").strip()
    if not key or any(c.isspace() for c in key):
        sys.exit("That does not look like a key.")
    status, data, _ = call("GET", "/v1/usage", key, timeout=30)
    if status != 200:
        fail_for(status, data)
    path = key_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"Key saved to {path} (not shown). Account: {data['label']} - {data['remaining']} of {data['limit']} images left "
          f"in each {data['window_hours']:g}-hour window.")


def cmd_usage(a):
    status, data, _ = call("GET", "/v1/usage", need_key(), timeout=30)
    if status != 200:
        fail_for(status, data)
    line = f"{data['used']}/{data['limit']} images used in the last {data['window_hours']:g} hours, {data['remaining']} left."
    if data.get("next_slot_free_in"):
        line += f" The next slot frees up in about {data['next_slot_free_in']}."
    print(line)


def cmd_models(a):
    status, data, _ = call("GET", "/v1/models", need_key(), timeout=30)
    if status != 200:
        fail_for(status, data)
    print("\n".join(m["id"] for m in data["data"]))


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, path in files:
        mime = RASTER[os.path.splitext(path)[1].lower()]
        out += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(path)}"\r\n'
                f"Content-Type: {mime}\r\n\r\n").encode()
        out += open(path, "rb").read() + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def out_paths(a, count, ext):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", a.prompt.lower()).strip("-")[:40] or "image"
    target = a.out or "walsync-images"
    if os.path.splitext(target)[1].lower() in (".png", ".jpg", ".jpeg", ".webp"):
        root, e = os.path.splitext(target)
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        return [target if count == 1 else f"{root}-{i + 1}{e}" for i in range(count)]
    os.makedirs(target, exist_ok=True)
    return [os.path.join(target, f"walsync-{stamp}-{slug}{'' if count == 1 else '-' + str(i + 1)}.{ext}") for i in range(count)]


def cmd_make(a, editing):
    key = need_key()
    if not a.prompt.strip():
        sys.exit("The prompt is empty.")
    if not 1 <= a.n <= 4:
        sys.exit("-n must be between 1 and 4.")
    model = MODEL_ALIASES.get(a.model, a.model)
    fields = {"model": model, "prompt": a.prompt, "n": a.n, "size": SIZES[a.aspect], "quality": a.quality}
    if editing:
        refs = a.image or []
        if not refs:
            sys.exit("edit needs at least one -i/--image.")
        if len(refs) > MAX_REFS:
            sys.exit(f"At most {MAX_REFS} images can be sent.")
        for p in refs:
            if not os.path.isfile(p):
                sys.exit(f"Image not found: {p}")
            if os.path.splitext(p)[1].lower() not in RASTER:
                sys.exit(f"Unsupported image type (use png, jpg, webp or gif): {p}")
            if os.path.getsize(p) > MAX_REF_BYTES:
                sys.exit(f"Image is over 25 MB: {p}")
        body, ctype = multipart(fields, [("image[]", p) for p in refs])
        path = "/v1/images/edits"
    else:
        body, ctype, path = json.dumps(fields).encode(), "application/json", "/v1/images/generations"

    for attempt in range(3):        # failures that were not charged (busy/backend/network) are retried twice
        status, data, headers = call("POST", path, key, body, ctype)
        if status == 200 and data.get("data"):
            break
        if status in (502, 503, 599) and attempt < 2:
            time.sleep(6 * (attempt + 1))
            continue
        fail_for(status, data)

    items = data["data"]
    ext = (data.get("output_format") or "png").lower().replace("jpeg", "jpg")
    for path_out, item in zip(out_paths(a, len(items), ext), items):
        with open(path_out, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
        print("IMAGE: " + os.path.abspath(path_out))
    meta = [f"model={model}"]
    if data.get("size"):
        meta.append(f"size={data['size']}")
    if data.get("quality"):
        meta.append(f"quality={data['quality']}")
    left = headers.get("X-Quota-Remaining")
    print("DONE: " + ", ".join(meta) + (f". Images left in your quota: {left}/{headers.get('X-Quota-Limit')}." if left is not None else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setkey"); s.add_argument("--stdin", action="store_true", help="read the key from standard input")
    sub.add_parser("usage"); sub.add_parser("models")
    for name in ("generate", "edit"):
        p = sub.add_parser(name)
        p.add_argument("prompt")
        p.add_argument("-m", "--model", default="flare")
        p.add_argument("-q", "--quality", default="auto", choices=QUALITIES)
        p.add_argument("-a", "--aspect", default="square", choices=list(SIZES))
        p.add_argument("-n", type=int, default=1)
        p.add_argument("-o", "--out")
        if name == "edit":
            p.add_argument("-i", "--image", action="append", help="source image (repeat for several)")
    a = ap.parse_args()
    {"setkey": cmd_setkey, "usage": cmd_usage, "models": cmd_models,
     "generate": lambda x: cmd_make(x, False), "edit": lambda x: cmd_make(x, True)}[a.cmd](a)


if __name__ == "__main__":
    main()
