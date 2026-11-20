"""Capture genuine execution evidence (API calls to the running Docker app, tests, docker ps)
and render each transcript as a terminal-style PNG.   Usage: python evidence.py <demo_account.json>"""
import json
import subprocess
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = HERE / "figs"; FIG.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8080/api"
acct = json.loads(Path(sys.argv[1]).read_text())


def render(name, title, lines, width=1700):
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)
    LH = 30
    img = Image.new("RGB", (width, 80 + LH * len(lines) + 20), "#1E1E1E")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, width, 48), fill="#333333")
    for i, c in enumerate(("#E5604E", "#F2A541", "#4CAF7A")):
        d.ellipse((18 + i * 30, 15, 36 + i * 30, 33), fill=c)
    d.text((120, 12), title, font=f, fill="#CCCCCC")
    for i, ln in enumerate(lines):
        col = "#9CDCFE" if ln.startswith(("$", ">", "PS ")) else "#E8E8E8"
        if "PASSED" in ln or "passed" in ln or " 200" in ln or " 201" in ln: col = "#8FD9A8"
        if "401" in ln or "415" in ln or "422" in ln: col = "#F2B36B"
        d.text((24, 64 + i * LH), ln[:int(width / 12.2)], font=f, fill=col)
    img.save(FIG / name)


def jl(obj, keep=None):
    if keep: obj = {k: obj[k] for k in keep if k in obj}
    return json.dumps(obj, indent=2).splitlines()


# ---------------- API session (local Docker deployment, demo test account)
s = requests.Session()
out = ["$ curl http://127.0.0.1:8080/api/health"]
r = s.get(f"{BASE}/health"); out += [f"HTTP {r.status_code}"] + jl(r.json())
out += ["", "$ POST /api/triage   (no session cookie)"]
img = ROOT / "data/kermany/chest_xray/test/PNEUMONIA/person1626_virus_2818.jpeg"
r = requests.post(f"{BASE}/triage", files={"file": (img.name, img.read_bytes(), "image/jpeg")})
out += [f"HTTP {r.status_code}  {r.json()}"]
r = s.post(f"{BASE}/auth/login", json={"email": acct["email"], "password": acct["password"], "remember": False})
out += ["", "$ POST /api/auth/login   {email, password}   -> HttpOnly session cookie set", f"HTTP {r.status_code}  user: {r.json().get('name')}"]
render("api_auth.png", "PneumoScope API - health and authentication", out)

out = [f"$ POST /api/triage  file={img.name}  (multipart/form-data)"]
r = s.post(f"{BASE}/triage", files={"file": (img.name, img.read_bytes(), "image/jpeg")})
res = r.json()
out += [f"HTTP {r.status_code}"] + jl(res, ["id", "filename", "prediction", "pneumonia_probability", "uncertainty",
                                            "decision", "decision_reason", "model_version", "processing_ms", "created_at"])
aid = res.get("id")
out += ["", "$ POST /api/triage  file=notes.txt (text/plain)"]
r = s.post(f"{BASE}/triage", files={"file": ("notes.txt", b"not an image", "text/plain")})
out += [f"HTTP {r.status_code}  {r.json()}"]
render("api_triage.png", "PneumoScope API - prediction request and validation", out)
evid = {"triage": res}

out = ["$ GET /api/model-info"]
r = s.get(f"{BASE}/model-info"); mi = r.json()
out += [f"HTTP {r.status_code}"] + json.dumps(mi, indent=1).splitlines()[:22]
render("api_model_info.png", "PneumoScope API - deployed model information", out)
evid["model_info"] = mi
if aid:
    r = s.post(f"{BASE}/analysis/{aid}/gradcam"); evid["gradcam_status"] = r.status_code
    s.delete(f"{BASE}/analysis/{aid}")
s.post(f"{BASE}/auth/logout")

# ---------------- tests
p = subprocess.run([str(ROOT / ".venv/Scripts/python"), "-m", "pytest", "-vv"], cwd=ROOT / "backend",
                   capture_output=True, text=True)
lines = [l for l in p.stdout.splitlines() if "::" in l or "passed" in l or "failed" in l]
evid["pytest_tail"] = lines[-1]
evid["pytest_count"] = sum(1 for l in lines if "PASSED" in l)
short = [l.split(" PASSED")[0].replace("tests/", "") + "  PASSED" for l in lines if "PASSED" in l]
render("pytest.png", "PS backend> python -m pytest -v", ["PS backend> python -m pytest -v"] + short[:26] + (
    [f"... ({len(short) - 26} more)"] if len(short) > 26 else []) + [lines[-1].strip("= ")], width=1500)

# ---------------- docker
dp = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], capture_output=True, text=True).stdout
di = subprocess.run(["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"], capture_output=True, text=True).stdout
di = "\n".join(l for l in di.splitlines() if l.startswith(("REPOSITORY", "pneumonia")))
render("docker.png", "PS Pneumonia> docker compose ps / images",
       ["PS Pneumonia> docker compose up --build -d", "PS Pneumonia> docker ps"] + dp.strip().splitlines()
       + ["", "PS Pneumonia> docker images"] + di.splitlines(), width=1700)
evid["docker_ps"] = dp; evid["docker_images"] = di
(HERE / "evidence.json").write_text(json.dumps(evid, indent=1))
print(json.dumps({k: v for k, v in evid.items() if k != "model_info"}, indent=1)[:2500])
