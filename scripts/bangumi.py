"""Render the Bangumi (bgm.tv) anime card for the profile README as a self-contained SVG.

Covers are inlined as data URIs: GitHub serves README images through a proxy that
blocks an SVG from loading anything external.

usage: python3 scripts/bangumi.py <bangumi_username> <out.svg>
"""

import base64
import json
import sys
import urllib.request
from html import escape

API = "https://api.bgm.tv/v0"
UA = "zzstar101/profile-readme (https://github.com/zzstar101/zzstar101)"
WISH, DONE, WATCHING = 1, 2, 3
SHOW = 6

W, CARD_W, CARD_H = 800, 112, 158
GAP = (W - SHOW * CARD_W) / (SHOW + 1)
TOP = 52
H = TOP + CARD_H + 62
ACCENT, MUTED = "#e11c1c", "#8b949e"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def collections(user: str, ctype: int, limit: int) -> dict:
    return json.loads(fetch(f"{API}/users/{user}/collections?subject_type=2&type={ctype}&limit={limit}"))


def data_uri(url: str) -> str:
    raw = fetch(url)
    mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def clip(text: str, width: int) -> str:
    """Cut text to `width` half-width cells (CJK counts as two), ending with an ellipsis."""
    out, used = "", 0
    for ch in text:
        cell = 1 if ord(ch) < 0x2E80 else 2
        if used + cell > width:
            return out.rstrip() + "…"
        out, used = out + ch, used + cell
    return out


def card(i: int, item: dict) -> str:
    s = item["subject"]
    x = GAP + i * (CARD_W + GAP)
    title = escape(clip(s.get("name_cn") or s["name"], 16))
    eps, seen = s.get("eps") or 0, item.get("ep_status") or 0
    parts = [
        f'<clipPath id="c{i}"><rect x="{x:.1f}" y="{TOP}" width="{CARD_W}" height="{CARD_H}" rx="8"/></clipPath>',
        f'<image href="{data_uri(s["images"]["small"])}" x="{x:.1f}" y="{TOP}" width="{CARD_W}" height="{CARD_H}" '
        f'preserveAspectRatio="xMidYMid slice" clip-path="url(#c{i})"/>',
        f'<text x="{x + CARD_W / 2:.1f}" y="{TOP + CARD_H + 22}" class="t">{title}</text>',
    ]
    if eps:
        bar_y = TOP + CARD_H + 32
        parts += [
            f'<rect x="{x:.1f}" y="{bar_y}" width="{CARD_W}" height="4" rx="2" fill="{MUTED}" opacity=".25"/>',
            f'<rect x="{x:.1f}" y="{bar_y}" width="{CARD_W * min(seen, eps) / eps:.1f}" height="4" rx="2" fill="{ACCENT}"/>',
            f'<text x="{x + CARD_W / 2:.1f}" y="{bar_y + 20}" class="p">{seen} / {eps} 话</text>',
        ]
    return "\n  ".join(parts)


def main(user: str, out: str) -> None:
    watching = collections(user, WATCHING, SHOW)
    heading, items = "在看", watching["data"]
    if not items:
        heading, items = "最近看过", collections(user, DONE, SHOW)["data"]
    totals = {k: collections(user, t, 1)["total"] for k, t in (("看过", DONE), ("在看", WATCHING), ("想看", WISH))}
    stats = " · ".join(f"{k} {v}" for k, v in totals.items())

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Bangumi {escape(user)}">
  <style>
    text {{ font-family: {FONT}; }}
    .h {{ font-size: 18px; font-weight: 700; fill: {ACCENT}; }}
    .s {{ font-size: 13px; fill: {MUTED}; text-anchor: end; }}
    .t {{ font-size: 13px; fill: {MUTED}; text-anchor: middle; }}
    .p {{ font-size: 11px; fill: {MUTED}; text-anchor: middle; opacity: .8; }}
  </style>
  <text x="{GAP:.1f}" y="32" class="h">Bangumi · {heading}</text>
  <text x="{W - GAP:.1f}" y="32" class="s">{stats}</text>
  {chr(10).join("  " + card(i, it) for i, it in enumerate(items[:SHOW])).lstrip()}
</svg>
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
