# -*- coding: utf-8 -*-
"""생성된 페이지의 본문 텍스트를 확인용으로 출력. 사용: python scripts/peek.py /2027/ [최대글자]"""
import sys, re, pathlib
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(__file__).resolve().parent.parent / "_site"
p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
f = root / p.strip("/") / "index.html" if p != "/" else root / "index.html"
t = f.read_text(encoding="utf-8")
title = re.search(r"<title>(.*?)</title>", t).group(1)
desc = re.search(r'name="description" content="(.*?)"', t).group(1)
m = re.search(r'<div class="cal-page">(.*?)</div>\s*<aside', t, re.S)
body = m.group(1)
body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
body = re.sub(r"</(tr|p|h1|h2|h3|li|div)>", "\n", body)
body = re.sub(r"</t[dh]>", " | ", body)
body = re.sub(r"<[^>]+>", "", body)
body = re.sub(r"\n\s*\n+", "\n", body)
print("TITLE:", title); print("DESC:", desc); print(body[:n])
