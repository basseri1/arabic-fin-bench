"""Verification stage (validate.py: sum relationships, anchoring, single-digit repair) per filing over pages32.
usage: python run32_validate.py <results_dir> <out_dir>"""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, ".")
import validate
res, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
manifest = json.loads(Path("pages32/manifest.json").read_text())
fixes = 0
for fid, pnos in manifest.items():
    pages = [f"{fid}_p{p:02d}" for p in pnos if (res / f"{fid}_p{p:02d}.md").exists()]
    if not pages: continue
    try:
        rep, _ = validate.validate_doc(str(res), pages)
        validate.apply_fixes(str(res), str(out), pages, rep); fixes += len(rep["fixes"])
    except Exception as e:                      # never lose a page: fall back to the unverified output
        print(f"[validate] {fid}: {type(e).__name__}: {e}", flush=True)
        for pg in pages: shutil.copy(res / f"{pg}.md", out / f"{pg}.md")
for pg in res.glob("*.md"):
    if not (out / pg.name).exists(): shutil.copy(pg, out / pg.name)
print(f"validate: {fixes} fixes -> {out}")
