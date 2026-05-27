"""Generate config.js from config.template.js and .env
Usage (PowerShell):
  python build_config.py
Creates config.js (ignored by git if added to .gitignore).
"""
from __future__ import annotations
import os, re, sys, pathlib
from typing import Dict

ROOT = pathlib.Path(__file__).parent
TEMPLATE = ROOT / "config.template.js"
OUTPUT = ROOT / "config.js"
ENV_FILE = ROOT / ".env"

# Simple .env parser

def load_env(path: pathlib.Path) -> Dict[str,str]:
    data: Dict[str,str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        if '=' not in line: continue
        k,v = line.split('=',1)
        data[k.strip()] = v.strip()
    return data

def apply_defaults(env: Dict[str,str]):
    env.setdefault('DEFAULT_COMPONENT','C1')
    env.setdefault('ROW_START','1')
    env.setdefault('ROW_END','9999')

PLACEHOLDER_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")

def render(template: str, env: Dict[str,str]) -> str:
    def repl(m):
        key = m.group(1)
        return env.get(key, "")
    return PLACEHOLDER_RE.sub(repl, template)

def main():
    env = load_env(ENV_FILE)
    apply_defaults(env)
    if not TEMPLATE.exists():
        print(f"Template missing: {TEMPLATE}", file=sys.stderr)
        return 1
    tpl = TEMPLATE.read_text(encoding='utf-8')
    out = render(tpl, env)
    OUTPUT.write_text(out, encoding='utf-8')
    print(f"Wrote {OUTPUT} (length {len(out)} bytes)")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
