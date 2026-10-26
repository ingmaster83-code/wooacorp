# -*- coding: utf-8 -*-
"""OpenDART 원본(_newdata/dart/*)을 사이트용 data/companies.json.gz 로 정리한다.
원본 수집: _newdata/dart_fetch.py (키는 _newdata/dart.env, 저장소에 넣지 않음).
사용: python scripts/build_data.py [원본폴더]"""
import sys, json, re, gzip, collections, pathlib
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "_newdata" / "dart"
FY = 2024

def num(s):
    if s is None: return None
    s = str(s).strip().replace(",", "")
    if s in ("", "-", "N/A"): return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try: v = float(s)
    except ValueError: return None
    return -v if neg else v

def jsonl(name):
    out = {}
    if not (SRC / (name + ".jsonl")).exists(): return out
    for l in (SRC / (name + ".jsonl")).open(encoding="utf-8"):
        x = json.loads(l); out[x["c"]] = x["r"]
    return out

# ───── 재무(주요계정) ─────
ACC = {"자산총계": "a", "부채총계": "l", "자본총계": "e", "매출액": "r", "영업이익": "o", "영업이익(손실)": "o", "당기순이익": "n", "당기순이익(손실)": "n", "법인세차감전 순이익": "p", "유동자산": "ca", "유동부채": "cl"}
raw = collections.defaultdict(lambda: collections.defaultdict(dict))      # corp → fs_div → year → {key: v}
for fname, base in (("multi_2024.json", 2024), ("multi_2022.json", 2022)):
    p = SRC / fname
    if not p.exists(): continue
    for r in json.loads(p.read_text(encoding="utf-8")):
        k = ACC.get(r["account_nm"])
        if not k or r["sj_div"] not in ("BS", "IS", "CIS"): continue
        for fld, off in (("thstrm_amount", 0), ("frmtrm_amount", 1), ("bfefrmtrm_amount", 2)):
            v = num(r.get(fld))
            if v is None: continue
            y = str(base - off)
            d = raw[r["corp_code"]][r["fs_div"]].setdefault(y, {})
            d.setdefault(k, v)

# ───── 보조 데이터 ─────
comp = jsonl("company"); emp = jsonl("empSttus"); alot = jsonl("alotMatter"); hold = jsonl("hyslrSttus"); hmv = jsonl("hmvAuditAllSttus")
SIDO = [("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"), ("광주", "광주"), ("대전", "대전"), ("울산", "울산"), ("세종", "세종"), ("경기", "경기"), ("강원", "강원"), ("충청북", "충북"), ("충북", "충북"),
        ("충청남", "충남"), ("충남", "충남"), ("전라북", "전북"), ("전북", "전북"), ("전라남", "전남"), ("전남", "전남"), ("경상북", "경북"), ("경북", "경북"), ("경상남", "경남"), ("경남", "경남"), ("제주", "제주")]
def sido_of(addr):
    a = (addr or "").strip()
    for pre, s in SIDO:
        if a.startswith(pre): return s
    return ""
def clean_name(n):
    s = re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사", "", n or "").strip()
    return s or (n or "").strip()

def parse_emp(rows):
    if not rows: return None
    tot = [r for r in rows if "합" in (r.get("fo_bbm") or "").replace(" ", "")]
    use = tot or rows
    gen = [r for r in use if r.get("sexdstn") in ("남", "여")]
    use = gen or use
    n = sum(num(r.get("sm")) or 0 for r in use)
    if n <= 0: return None
    m = sum(num(r.get("sm")) or 0 for r in use if r.get("sexdstn") == "남")
    f = sum(num(r.get("sm")) or 0 for r in use if r.get("sexdstn") == "여")
    w = [(num(r.get("sm")), num(r.get("jan_salary_am"))) for r in use]
    w = [(a, b) for a, b in w if a and b]
    sal = (sum(a * b for a, b in w) / sum(a for a, _ in w)) if w else None
    tt = sum(num(r.get("fyer_salary_totamt")) or 0 for r in use) or None
    if sal is None and tt: sal = tt / n
    if sal is not None:
        if sal < 1e6:                                            # 천원·백만원 단위로 적은 보고서 보정
            if 1e7 <= sal * 1e3 <= 5e8: sal *= 1e3
            elif 1e7 <= sal * 1e6 <= 5e8: sal *= 1e6
            else: sal = None
        elif sal > 3e9: sal = None
    if tt and sal and not (0.2 <= tt / (sal * n) <= 5): tt = None
    yw = [(num(r.get("sm")), num(r.get("avrg_cnwk_sdytrn"))) for r in use]
    yw = [(a, b) for a, b in yw if a and b is not None]
    yr = round(sum(a * b for a, b in yw) / sum(a for a, _ in yw), 1) if yw else None
    return {"n": int(n), "sal": int(round(sal)) if sal else None, "yr": yr, "tot": tt, "m": int(m) if m or f else None, "f": int(f) if m or f else None}

def parse_div(rows):
    if not rows: return None
    ys = {"thstrm": str(FY), "frmtrm": str(FY - 1), "lwfr": str(FY - 2)}
    out = {"dps": {}, "yld": {}, "pay": {}, "tot": {}}
    for r in rows:
        se = (r.get("se") or "").replace(" ", ""); kind = (r.get("stock_knd") or "").strip()
        key = None
        if "주당현금배당금" in se and kind in ("보통주", "-", ""): key = "dps"
        elif "현금배당수익률" in se and kind in ("보통주", "-", ""): key = "yld"
        elif "현금배당성향" in se: key = "pay"
        elif "현금배당금총액" in se: key = "tot"
        if not key: continue
        for fld, y in ys.items():
            v = num(r.get(fld))
            if v is not None and y not in out[key]: out[key][y] = v
    if not any(out["dps"].values()): return None
    return out

def parse_hold(rows):
    if not rows: return None
    com = [r for r in rows if (r.get("stock_knd") or "").strip() in ("보통주", "의결권 있는 주식", "")] or rows
    top = next((r for r in com if "최대주주" in (r.get("relate") or "") and "본인" in (r.get("relate") or "")), None) or next((r for r in com if "본인" in (r.get("relate") or "")), None)
    sumrow = next((r for r in com if (r.get("nm") or "").strip() in ("계", "합계", "합 계")), None)
    allrt = num(sumrow.get("trmend_posesn_stock_qota_rt")) if sumrow else None
    if allrt is None:
        v = [num(r.get("trmend_posesn_stock_qota_rt")) for r in com if (r.get("nm") or "").strip() not in ("계", "합계")]
        v = [x for x in v if x is not None]
        allrt = round(sum(v), 2) if v else None
    if not top and allrt is None: return None
    return {"top": (top.get("nm") or "").strip() if top else None, "rt": num(top.get("trmend_posesn_stock_qota_rt")) if top else None,
            "sh": int(num(top.get("trmend_posesn_stock_co"))) if top and num(top.get("trmend_posesn_stock_co")) else None, "all": allrt, "stlm": (rows[0].get("stlm_dt") or "")}

def parse_exec(rows):
    if not rows: return None
    r = rows[0]; avg = num(r.get("jan_avrg_mendng_am")); tot = num(r.get("mendng_totamt"))
    if not avg: return None
    return {"n": int(num(r.get("nmpr")) or 0) or None, "avg": avg, "tot": tot}

out = []
for cid, c in comp.items():
    if c.get("status") != "000": continue
    fsd = raw.get(cid)
    if not fsd: continue
    fs = "CFS" if (fsd.get("CFS", {}).get(str(FY), {}).get("a") is not None) else "OFS"
    yrs = fsd.get(fs) or {}
    if yrs.get(str(FY), {}).get("a") is None: continue
    fy = {y: {k: v for k, v in d.items() if k in ("a", "l", "e", "r", "o", "n")} for y, d in yrs.items() if int(y) <= FY}
    sc = (c.get("stock_code") or "").strip()
    rec = {"id": cid, "n": clean_name(c.get("corp_name")), "sc": sc, "cl": c.get("corp_cls") or "E", "ad": (c.get("adres") or "").strip(), "sido": sido_of(c.get("adres")),
           "ind": ((c.get("induty_code") or "")[:5] if (c.get("induty_code") or "").startswith("64992") else (c.get("induty_code") or "")[:2]), "est": (c.get("est_dt") or "").strip(), "acc": (c.get("acc_mt") or "").strip(), "hp": (c.get("hm_url") or "").strip(), "fs": fs, "fy": fy}
    e = parse_emp(emp.get(cid, {}).get("list")) if emp.get(cid, {}).get("status") == "000" else None
    if e: rec["emp"] = e
    dv = parse_div(alot.get(cid, {}).get("list")) if alot.get(cid, {}).get("status") == "000" else None
    if dv: rec["div"] = dv
    h = parse_hold(hold.get(cid, {}).get("list")) if hold.get(cid, {}).get("status") == "000" else None
    if h: rec["hold"] = h
    x = parse_exec(hmv.get(cid, {}).get("list")) if hmv.get(cid, {}).get("status") == "000" else None
    if x: rec["exec"] = x
    out.append(rec)

out.sort(key=lambda r: r["id"])
meta = {"asof": "%d 사업연도(%d년 공시)" % (FY, FY + 1), "fy": str(FY), "companies": out}
dst = ROOT / "data" / "companies.json.gz"
dst.parent.mkdir(exist_ok=True)
with gzip.open(dst, "wt", encoding="utf-8", compresslevel=9) as f: json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
cnt = collections.Counter()
for r in out:
    for k in ("emp", "div", "hold", "exec"):
        if k in r: cnt[k] += 1
print("companies", len(out), dict(cnt), "bytes", dst.stat().st_size)
