# -*- coding: utf-8 -*-
"""우아기업 정적 사이트 생성기 → _site/.  사용: python scripts/build_site.py
입력: data/companies.json.gz (build_data.py가 OpenDART 응답을 정리한 것)"""
import sys, json, re, gzip, shutil, time, collections, statistics
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *

META = json.loads(gzip.open(ROOT / "data" / "companies.json.gz", "rt", encoding="utf-8").read())
ASOF = META["asof"]                       # 예: "2024 회계연도(2025년 공시)"
FY = META["fy"]                           # "2024"
DATA = META["companies"]
YEARS = [str(y) for y in range(int(FY), int(FY) - 5, -1)]     # 2024..2020
MK = {"Y": "코스피", "K": "코스닥", "N": "코넥스", "E": "비상장"}
KSIC = {"01": "작물 재배업", "02": "임업", "03": "어업", "05": "석탄·원유·천연가스 광업", "06": "금속 광업", "07": "비금속광물 광업", "08": "광업 지원 서비스업", "10": "식료품 제조업", "11": "음료 제조업", "12": "담배 제조업",
        "13": "섬유제품 제조업", "14": "의복·모피제품 제조업", "15": "가죽·가방·신발 제조업", "16": "목재·나무제품 제조업", "17": "펄프·종이제품 제조업", "18": "인쇄·기록매체 복제업", "19": "코크스·석유정제품 제조업",
        "20": "화학물질·화학제품 제조업", "21": "의료용 물질·의약품 제조업", "22": "고무·플라스틱제품 제조업", "23": "비금속 광물제품 제조업", "24": "1차 금속 제조업", "25": "금속 가공제품 제조업",
        "26": "전자부품·컴퓨터·영상·통신장비 제조업", "27": "의료·정밀·광학기기 제조업", "28": "전기장비 제조업", "29": "기타 기계·장비 제조업", "30": "자동차·트레일러 제조업", "31": "기타 운송장비 제조업",
        "32": "가구 제조업", "33": "기타 제품 제조업", "34": "산업용 기계·장비 수리업", "35": "전기·가스·증기 공급업", "36": "수도업", "37": "하수·폐수 처리업", "38": "폐기물 처리·원료 재생업", "39": "환경 정화·복원업",
        "41": "종합 건설업", "42": "전문직별 공사업", "45": "자동차 및 부품 판매업", "46": "도매 및 상품 중개업", "47": "소매업", "49": "육상 운송·파이프라인 운송업", "50": "수상 운송업", "51": "항공 운송업",
        "52": "창고·운송 관련 서비스업", "55": "숙박업", "56": "음식점·주점업", "58": "출판업", "59": "영상·오디오 기록물 제작·배급업", "60": "방송업", "61": "통신업", "62": "컴퓨터 프로그래밍·시스템 통합업",
        "63": "정보서비스업", "64": "금융업", "64992": "지주회사", "65": "보험·연금업", "66": "금융·보험 관련 서비스업", "68": "부동산업", "70": "연구개발업", "71": "전문 서비스업", "72": "건축기술·엔지니어링 서비스업", "73": "기타 과학기술 서비스업",
        "74": "사업시설 관리·조경 서비스업", "75": "사업 지원 서비스업", "76": "임대업", "84": "공공행정", "85": "교육 서비스업", "86": "보건업", "87": "사회복지 서비스업", "90": "창작·예술·여가 서비스업",
        "91": "스포츠·오락 서비스업", "94": "협회·단체", "95": "개인·소비용품 수리업", "96": "기타 개인 서비스업"}

# ───────────────────────── 서식 ─────────────────────────
def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)
def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def sl(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"

def fw(x):
    """원 → '1조 2,345억원' / '345억원' / '1,234만원'"""
    if x is None: return "-"
    neg = x < 0; a = abs(x)
    if a >= 1e12:
        jo = int(a // 1e12); eok = int(round((a - jo * 1e12) / 1e8))
        if eok >= 10000: jo += 1; eok = 0
        s = "%s조" % "{:,}".format(jo) + (" %s억" % "{:,}".format(eok) if eok else "") + "원"
    elif a >= 1e8: s = "%s억원" % "{:,}".format(int(round(a / 1e8)))
    elif a >= 1e4: s = "%s만원" % "{:,}".format(int(round(a / 1e4)))
    else: s = "%s원" % "{:,}".format(int(round(a)))
    return ("-" + s) if neg else s
def fe(x):
    """표용 짧은 표기: 억원 단위"""
    if x is None: return "-"
    return "{:,}".format(int(round(x / 1e8)))
def pct(x, d=1):
    if x is None: return "-"
    return ("%." + str(d) + "f%%") % x
def num(x): return "-" if x is None else "{:,}".format(int(round(x)))
def man(x): return "-" if x is None else "{:,}만원".format(int(round(x / 1e4)))
def sgn(x): return "증가" if x > 0 else "감소" if x < 0 else "동일"

# ───────────────────────── 데이터 가공 ─────────────────────────
SIDO_FULL = {"서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도", "강원": "강원특별자치도",
             "충북": "충청북도", "충남": "충청남도", "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도", "제주": "제주특별자치도"}
used = set()
for d in DATA:
    base = sl(d["n"]) + "-" + (d["sc"] or d["id"]); s = base; k = 2
    while s in used: s = "%s-%d" % (base, k); k += 1
    used.add(s); d["slug"] = s; d["path"] = "/company/%s/" % s
    d["mk"] = MK.get(d["cl"], "비상장")
    d["ind2"] = d["ind"] if d["ind"] in KSIC else ""
    d["indn"] = KSIC.get(d["ind2"], "")
    f = d["fy"].get(FY) or {}
    d["cur"] = f; p = d["fy"].get(str(int(FY) - 1)) or {}
    d["prev"] = p
    d["debt"] = (f["l"] / f["e"] * 100) if f.get("l") is not None and f.get("e") and f["e"] > 0 else None
    d["margin"] = (f["o"] / f["r"] * 100) if f.get("o") is not None and f.get("r") and f["r"] > 0 else None
    d["roe"] = (f["n"] / f["e"] * 100) if f.get("n") is not None and f.get("e") and f["e"] > 0 else None
    d["growth"] = ((f["r"] - p["r"]) / p["r"] * 100) if f.get("r") and p.get("r") and p["r"] > 0 else None
    d["sal"] = (d.get("emp") or {}).get("sal")
    d["empn"] = (d.get("emp") or {}).get("n")
    dv = d.get("div") or {}
    d["dps"] = (dv.get("dps") or {}).get(FY)
    d["yld"] = (dv.get("yld") or {}).get(FY)
BY_IND = collections.defaultdict(list); BY_SIDO = collections.defaultdict(list)
for d in DATA:
    if d["ind2"]: BY_IND[d["ind2"]].append(d)
    if d.get("sido"): BY_SIDO[d["sido"]].append(d)
SIDOS = [s for s in SIDO_FULL if s in BY_SIDO]

def rankof(d, lst, getter, rev=True):
    vals = [(getter(x), x["id"]) for x in lst if getter(x) is not None]
    vals.sort(key=lambda t: (-t[0] if rev else t[0], t[1]))
    for i, (_, id_) in enumerate(vals):
        if id_ == d["id"]: return i + 1, len(vals)
    return None, len(vals)
def med(lst, getter):
    v = [getter(x) for x in lst if getter(x) is not None]
    return statistics.median(v) if len(v) >= 3 else None

# 순위 정의: (키, 표시명, 값 getter, 표시 함수, 내림차순 여부, 제목용 설명)
METRICS = [
    ("revenue", "매출액", lambda d: d["cur"].get("r"), lambda d: fw(d["cur"].get("r")), True, "매출액이 큰"),
    ("operating-profit", "영업이익", lambda d: d["cur"].get("o"), lambda d: fw(d["cur"].get("o")), True, "영업이익이 큰"),
    ("net-income", "당기순이익", lambda d: d["cur"].get("n"), lambda d: fw(d["cur"].get("n")), True, "당기순이익이 큰"),
    ("assets", "자산총계", lambda d: d["cur"].get("a"), lambda d: fw(d["cur"].get("a")), True, "자산이 큰"),
    ("margin", "영업이익률", lambda d: d["margin"] if d["cur"].get("r") and d["cur"]["r"] >= 1e10 else None, lambda d: pct(d["margin"]), True, "영업이익률이 높은"),
    ("debt-ratio", "부채비율", lambda d: d["debt"], lambda d: pct(d["debt"], 0), False, "부채비율이 낮은"),
    ("salary", "1인 평균급여", lambda d: d["sal"], lambda d: man(d["sal"]), True, "직원 1인 평균급여가 높은"),
    ("employees", "직원 수", lambda d: d["empn"], lambda d: ("%s명" % num(d["empn"])) if d["empn"] else "-", True, "직원 수가 많은"),
    ("dividend", "배당수익률", lambda d: d["yld"] if d["yld"] and 0 < d["yld"] <= 30 else None, lambda d: pct(d["yld"], 2), True, "현금배당수익률이 높은"),
]
MET = {m[0]: m for m in METRICS}
HAS = {m[0]: sum(1 for d in DATA if m[2](d) is not None) >= 10 for m in METRICS}
def rk(key, label): return [(label, "/rank/%s/" % key)] if HAS[key] else []
def metric_rank(d, key, lst=None):
    m = MET[key]; return rankof(d, lst if lst is not None else DATA, m[2], m[4])

# ───────────────────────── 공용 블록 ─────────────────────────
NOTE = ("모든 수치는 금융감독원 전자공시시스템(DART) 오픈API로 제공되는 %s 사업보고서 기준이며 단위는 원 또는 억원입니다. 연결재무제표가 있으면 연결, 없으면 별도 기준을 사용했습니다. "
        "정정공시나 이후 실적은 반영되지 않을 수 있으므로 투자·거래 전 DART 원문을 확인하세요. 투자 권유가 아닌 참고용 자료입니다." % ASOF)
H_COMP = ["회사", "구분", "업종", "매출액", "영업이익"]
def comp_link(d): return '<a href="%s">%s</a>' % (d["path"], esc(d["n"]))
def rows_basic(lst): return [[comp_link(d), d["mk"], esc(d["indn"] or "-"), fw(d["cur"].get("r")), fw(d["cur"].get("o"))] for d in lst]
def fs_label(d): return "연결" if d["fs"] == "CFS" else "별도"
def stock_txt(d): return ("종목코드 %s" % d["sc"]) if d["sc"] else "비상장"
def ind_chip(d): return [(d["indn"] + " 기업", "/industry/%s/" % d["ind2"])] if d["ind2"] else []

def nearby_block(d, n=8):
    if not d["ind2"]: return ""
    lst = sorted([x for x in BY_IND[d["ind2"]] if x is not d and x["cur"].get("r")], key=lambda x: -x["cur"]["r"])
    if d["cur"].get("r"):
        r = d["cur"]["r"]; lst = sorted(lst, key=lambda x: abs(x["cur"]["r"] - r))[:n]
        lst.sort(key=lambda x: -x["cur"]["r"])
    else: lst = lst[:n]
    if not lst: return ""
    return '<h2 class="group-title">🏭 같은 업종(%s) 비슷한 규모 기업</h2>' % esc(d["indn"]) + table(H_COMP, rows_basic(lst), (3, 4))

def sub_chips(d):
    items = [(d["n"] + " 재무", d["path"])]
    if d["empn"] or d["sal"]: items.append((d["n"] + " 평균연봉", d["path"] + "salary/"))
    if d["dps"]: items.append((d["n"] + " 배당금", d["path"] + "dividend/"))
    if d.get("hold") and d["hold"].get("top"): items.append((d["n"] + " 최대주주", d["path"] + "shareholders/"))
    return items

def crumbs_for(d, label=None, sub=""):
    c = [("홈", "/"), ("기업", "/company/")]
    if d["ind2"]: c.append((d["indn"], "/industry/%s/" % d["ind2"]))
    c.append((d["n"], d["path"]))
    if label: c.append((label, d["path"] + sub))
    return c

def org_ld(d):
    o = {"@context": "https://schema.org", "@type": "Corporation", "name": d["n"]}
    if d.get("ad"): o["address"] = {"@type": "PostalAddress", "streetAddress": d["ad"], "addressCountry": "KR"}
    if d.get("est") and len(d["est"]) == 8: o["foundingDate"] = "%s-%s-%s" % (d["est"][:4], d["est"][4:6], d["est"][6:])
    if d["sc"]: o["tickerSymbol"] = d["sc"]
    return [o]

# ───────────────────────── 기업 메인(재무) ─────────────────────────
def page_company(d):
    f, p = d["cur"], d["prev"]; yrs = [y for y in YEARS if d["fy"].get(y)]
    rk_rev, n_rev = metric_rank(d, "revenue")
    ind_rk = rankof(d, BY_IND[d["ind2"]], MET["revenue"][2]) if d["ind2"] else (None, 0)
    parts = []
    if f.get("r") is not None: parts.append("매출액 <b>%s</b>" % fw(f["r"]))
    if f.get("o") is not None: parts.append("영업이익 <b>%s</b>%s" % (fw(f["o"]), "(적자)" if f["o"] < 0 else ""))
    if f.get("n") is not None: parts.append("당기순이익 <b>%s</b>%s" % (fw(f["n"]), "(적자)" if f["n"] < 0 else ""))
    gr = ""
    if d["growth"] is not None: gr = " 전년 대비 매출은 %.1f%% %s했습니다." % (abs(d["growth"]), sgn(d["growth"]))
    lead = ('<p class="lead"><b>%s</b>(%s, %s)은(는) %s%s 기업입니다. %s년 사업보고서(%s 기준)에서 %s입니다.%s 자산총계는 %s, 부채비율은 %s입니다.</p>' % (
        esc(d["n"]), d["mk"], stock_txt(d), esc((SIDO_FULL.get(d.get("sido"), "") + " ") if d.get("sido") else ""), esc(d["indn"]) if d["indn"] else "", FY, fs_label(d), ", ".join(parts) or "주요 손익 항목이 공시되지 않았습니다",
        gr, fw(f.get("a")), pct(d["debt"], 0)))
    prof = [["회사명", esc(d["n"])], ["구분", d["mk"] + ((" · 종목코드 " + d["sc"]) if d["sc"] else "")], ["업종", esc(d["indn"] or "-")], ["본사 주소", esc(d.get("ad") or "-")],
            ["설립일", ("%s년 %s월 %s일" % (d["est"][:4], int(d["est"][4:6]), int(d["est"][6:]))) if d.get("est") and len(d["est"]) == 8 and d["est"].isdigit() else "-"], ["결산월", ("%s월" % d["acc"]) if d.get("acc") else "-"]]
    if d.get("hp"): prof.append(["홈페이지", esc(d["hp"])])
    if rk_rev: prof.append(["매출액 순위", "전체 %s위 / %s개 사업보고서 제출 기업" % (num(rk_rev), num(n_rev))])
    if ind_rk[0]: prof.append(["업종 내 매출 순위", "%s위 / %s개" % (num(ind_rk[0]), num(ind_rk[1]))])
    t_prof = table(["항목", "내용"], prof)
    hd = ["항목"] + ["%s년" % y for y in yrs]
    def line(label, k): return [label] + [fe(d["fy"][y].get(k)) for y in yrs]
    fin_rows = [line("매출액(억원)", "r"), line("영업이익(억원)", "o"), line("당기순이익(억원)", "n"), line("자산총계(억원)", "a"), line("부채총계(억원)", "l"), line("자본총계(억원)", "e")]
    def ratio(y, a, b):
        v = d["fy"][y]; return (v[a] / v[b] * 100) if v.get(a) is not None and v.get(b) and v[b] > 0 else None
    fin_rows.append(["부채비율"] + [pct(ratio(y, "l", "e"), 0) for y in yrs])
    fin_rows.append(["영업이익률"] + [pct(ratio(y, "o", "r")) for y in yrs])
    t_fin = table(hd, fin_rows, tuple(range(1, len(hd))))
    notes = []
    if f.get("r") and p.get("r"):
        notes.append("%s년 매출액은 %s으로 전년(%s)보다 %s했습니다." % (FY, fw(f["r"]), fw(p["r"]), sgn(f["r"] - p["r"])))
    if f.get("o") is not None and p.get("o") is not None:
        if f["o"] >= 0 and p["o"] > 0: notes.append("영업이익은 %s으로 전년 대비 %.1f%% %s했습니다." % (fw(f["o"]), abs((f["o"] - p["o"]) / p["o"] * 100), sgn(f["o"] - p["o"])))
        elif f["o"] < 0 <= p["o"]: notes.append("전년 영업이익 %s에서 %s 영업손실로 돌아섰습니다." % (fw(p["o"]), fw(abs(f["o"]))))
        elif f["o"] >= 0 > p["o"]: notes.append("전년 영업손실 %s에서 %s 영업이익으로 흑자 전환했습니다." % (fw(abs(p["o"])), fw(f["o"])))
        elif f["o"] < 0 and p["o"] < 0: notes.append("영업손실이 이어져 %s년 영업손실은 %s입니다." % (FY, fw(abs(f["o"]))))
    if d["debt"] is not None:
        im = med(BY_IND[d["ind2"]], lambda x: x["debt"]) if d["ind2"] else None
        notes.append("부채비율은 %s로 %s" % (pct(d["debt"], 0), ("같은 업종 중앙값(%s)보다 %s 편입니다." % (pct(im, 0), "높은" if d["debt"] > im else "낮은")) if im is not None else "100%를 기준으로 재무 안정성을 가늠하는 지표입니다."))
    if d["margin"] is not None:
        im = med(BY_IND[d["ind2"]], lambda x: x["margin"]) if d["ind2"] else None
        notes.append("영업이익률은 %s%s" % (pct(d["margin"]), ("로 같은 업종 중앙값(%s)보다 %s 수준입니다." % (pct(im), "높은" if d["margin"] > im else "낮은")) if im is not None else "입니다."))
    body_notes = "<p class=\"lead\">%s</p>" % " ".join(notes) if notes else ""
    summ = []
    if d["empn"]: summ.append("직원 %s명" % num(d["empn"]) + (", 1인 평균급여 %s" % man(d["sal"]) if d["sal"] else ""))
    if d["dps"]: summ.append("주당 현금배당 %s원" % num(d["dps"]))
    if d.get("hold") and d["hold"].get("top"): summ.append("최대주주 %s(지분 %s)" % (esc(d["hold"]["top"]), pct(d["hold"].get("rt"), 2)))
    sumbox = ('<h2 class="group-title">📌 함께 보기</h2><p class="lead">%s. 아래 링크에서 자세히 볼 수 있습니다.</p>' % " · ".join(summ)) if summ else ""
    body = f"""
<div class="page-head"><h1>{esc(d['n'])} 매출·영업이익·재무제표 ({FY}년)</h1><p>{d['mk']} · {esc(d['indn'] or '기업')} · {fs_label(d)}재무제표 · {ASOF}</p></div>
{lead}
{ad()}
<h2 class="group-title">🏢 기업 정보</h2>
{t_prof}
<h2 class="group-title">📊 최근 {len(yrs)}개년 재무 요약</h2>
{t_fin}
{body_notes}
{sumbox}
{chips(sub_chips(d))}
{nearby_block(d)}
<p class="note">{NOTE}</p>
{chips(ind_chip(d) + rk("revenue", "매출 순위") + rk("salary", "평균연봉 순위") + rk("dividend", "배당 순위"))}
"""
    faq = []
    if f.get("r") is not None: faq.append(("%s 매출액은 얼마인가요?" % d["n"], "DART %s년 사업보고서 기준 %s 매출액은 %s입니다%s." % (FY, fs_label(d), fw(f["r"]), (" (전년 %s)" % fw(p["r"])) if p.get("r") else "")))
    if f.get("o") is not None: faq.append(("%s 영업이익은 얼마인가요?" % d["n"], "%s년 %s 영업이익은 %s%s입니다." % (FY, fs_label(d), fw(f["o"]), "(영업손실)" if f["o"] < 0 else "")))
    if d["debt"] is not None: faq.append(("%s 부채비율은 얼마인가요?" % d["n"], "%s년말 부채총계 %s, 자본총계 %s로 부채비율은 %s입니다." % (FY, fw(f.get("l")), fw(f.get("e")), pct(d["debt"], 0))))
    faq.append(("이 정보는 어디서 가져왔나요?", "금융감독원 전자공시시스템(DART) 오픈API의 사업보고서 재무 정보를 그대로 정리한 것입니다. 정정공시는 반영되지 않을 수 있습니다."))
    desc = "%s %s년 매출액 %s, 영업이익 %s, 당기순이익 %s. 최근 %d개년 재무제표 요약과 부채비율·영업이익률, 업종 내 순위." % (d["n"], FY, fw(f.get("r")), fw(f.get("o")), fw(f.get("n")), len(yrs))
    write(d["path"], layout(d["path"], "%s 매출·영업이익·재무제표 (%s년)" % (d["n"], FY), desc, body, faq, crumbs_for(d), extra_ld=org_ld(d)), "0.6")

# ───────────────────────── 평균연봉 ─────────────────────────
def page_salary(d):
    e = d["emp"]; path = d["path"] + "salary/"
    sal, n = e.get("sal"), e.get("n")
    sal_rk = metric_rank(d, "salary") if sal else (None, 0)
    ind_rk = rankof(d, BY_IND[d["ind2"]], MET["salary"][2]) if (sal and d["ind2"]) else (None, 0)
    im = med(BY_IND[d["ind2"]], lambda x: x["sal"]) if d["ind2"] else None
    allm = med(DATA, lambda x: x["sal"])
    parts = []
    if n: parts.append("직원 수는 <b>%s명</b>" % num(n))
    if sal: parts.append("1인 평균급여액은 <b>%s</b>" % man(sal))
    if e.get("yr"): parts.append("평균 근속연수는 <b>%s년</b>" % e["yr"])
    cmp_ = ""
    if sal and allm: cmp_ = " 이는 사업보고서 제출 기업 중앙값(%s)보다 %s 수준입니다." % (man(allm), "높은" if sal > allm else "낮은")
    lead = '<p class="lead"><b>%s</b>의 %s년 사업보고서(%s)에서 %s입니다.%s 직원 현황은 사업보고서 기준일 현재이며 1인 평균급여액은 사업보고서에 공시된 값입니다.</p>' % (esc(d["n"]), FY, ASOF, ", ".join(parts), cmp_)
    rows = [["직원 수", ("%s명" % num(n)) if n else "-"], ["1인 평균급여액", man(sal)], ["연간 급여 총액", fw(e.get("tot")) if e.get("tot") else "-"], ["평균 근속연수", ("%s년" % e["yr"]) if e.get("yr") else "-"]]
    if e.get("m") is not None and e.get("f") is not None: rows.append(["성별 직원 수", "남 %s명 · 여 %s명" % (num(e["m"]), num(e["f"]))])
    if sal_rk[0]: rows.append(["평균급여 전체 순위", "%s위 / %s개 기업" % (num(sal_rk[0]), num(sal_rk[1]))])
    if ind_rk[0]: rows.append(["업종 내 평균급여 순위", "%s위 / %s개 (%s)" % (num(ind_rk[0]), num(ind_rk[1]), esc(d["indn"]))])
    if im and sal: rows.append(["업종 중앙값 대비", "%s (업종 중앙값 %s)" % (("%+.0f%%" % ((sal - im) / im * 100)), man(im))])
    t1 = table(["항목", "내용"], rows)
    ex = d.get("exec") or {}
    exb = ""
    if ex.get("avg") and sal:
        exb = '<h2 class="group-title">👔 임원 보수</h2><p class="lead">이사·감사 전체(%s명)의 1인 평균 보수액은 <b>%s</b>, 보수 총액은 %s입니다. 직원 1인 평균급여의 약 %.1f배 수준입니다.</p>' % (num(ex.get("n")), fw(ex["avg"]), fw(ex.get("tot")), ex["avg"] / sal)
    nb = ""
    if d["ind2"]:
        near = sorted([x for x in BY_IND[d["ind2"]] if x["sal"] and x is not d], key=lambda x: abs(x["sal"] - (sal or 0)))[:8]
        near.sort(key=lambda x: -x["sal"])
        if near: nb = '<h2 class="group-title">🏭 같은 업종 평균급여 비교</h2>' + table(["회사", "구분", "1인 평균급여", "직원 수"], [[comp_link(x), x["mk"], man(x["sal"]), num(x["empn"])] for x in near], (2, 3))
    body = f"""
<div class="page-head"><h1>{esc(d['n'])} 평균연봉·직원 수 ({FY}년)</h1><p>{d['mk']} · {esc(d['indn'] or '기업')} · {ASOF}</p></div>
{lead}
{ad()}
<h2 class="group-title">💰 직원 현황</h2>
{t1}
{exb}
{nb}
<p class="note">1인 평균급여액은 사업보고서에 공시된 값으로 상여·성과급 등이 포함된 금액이며 직급·근속에 따라 개인별로 크게 다를 수 있습니다. 근로소득 실수령액은 세금·4대보험을 공제해야 하므로 <a href="https://wooayeonbong.wooahouse.com">우아연봉</a>에서 계산해 볼 수 있습니다. {NOTE}</p>
{chips(sub_chips(d))}
{chips(rk("salary", "평균연봉 순위") + rk("employees", "직원 수 순위") + ind_chip(d))}
"""
    faq = []
    if sal: faq.append(("%s 평균연봉은 얼마인가요?" % d["n"], "%s년 사업보고서 기준 1인 평균급여액은 %s입니다%s." % (FY, man(sal), (" (직원 %s명)" % num(n)) if n else "")))
    if n: faq.append(("%s 직원은 몇 명인가요?" % d["n"], "%s년 사업보고서 기준 직원 수는 %s명입니다%s." % (FY, num(n), (" (평균 근속연수 %s년)" % e["yr"]) if e.get("yr") else "")))
    faq.append(("평균급여에 성과급도 포함되나요?", "사업보고서의 1인 평균급여액은 연간 급여 총액을 직원 수로 나눈 값으로 상여금·성과급 등이 포함된 경우가 많습니다. 세전 금액입니다."))
    desc = "%s %s년 1인 평균급여 %s, 직원 수 %s명%s. 업종·전체 순위와 임원 보수, 같은 업종 평균연봉 비교." % (d["n"], FY, man(sal), num(n), (", 평균 근속 %s년" % e["yr"]) if e.get("yr") else "")
    write(path, layout(path, "%s 평균연봉·직원 수 (%s년)" % (d["n"], FY), desc, body, faq, crumbs_for(d, "평균연봉", "salary/"), extra_ld=org_ld(d)), "0.6")

# ───────────────────────── 배당 ─────────────────────────
def page_dividend(d):
    dv = d["div"]; path = d["path"] + "dividend/"
    ys = [y for y in YEARS if y in (dv.get("dps") or {})]
    cur = (dv.get("dps") or {}).get(FY); yl = (dv.get("yld") or {}).get(FY); pay = (dv.get("pay") or {}).get(FY); tot = (dv.get("tot") or {}).get(FY)
    parts = []
    if cur: parts.append("주당 현금배당금은 <b>%s원</b>" % num(cur))
    if yl: parts.append("현금배당수익률은 <b>%s</b>" % pct(yl, 2))
    if pay: parts.append("현금배당성향은 <b>%s</b>" % pct(pay, 1))
    if tot: parts.append("현금배당금 총액은 <b>%s</b>" % fw(tot * 1e6))
    yr_rank = metric_rank(d, "dividend") if yl and yl > 0 else (None, 0)
    lead = '<p class="lead"><b>%s</b>의 %s년 보통주 기준 %s입니다. %s배당은 사업보고서 \'배당에 관한 사항\'에 공시된 값이며 배당수익률은 결산기말 주가 기준입니다.</p>' % (
        esc(d["n"]), FY, ", ".join(parts), ("배당수익률 전체 순위는 %s위(%s개 배당 기업 중)입니다. " % (num(yr_rank[0]), num(yr_rank[1]))) if yr_rank[0] else "")
    def row(label, k, fmt):
        return [label] + [fmt((dv.get(k) or {}).get(y)) for y in ys]
    hd = ["항목"] + ["%s년" % y for y in ys]
    rws = [row("주당 현금배당금(원)", "dps", lambda v: num(v) if v is not None else "-"), row("현금배당수익률", "yld", lambda v: pct(v, 2) if v is not None else "-"),
           row("현금배당성향", "pay", lambda v: pct(v, 1) if v is not None else "-"), row("현금배당금 총액(억원)", "tot", lambda v: "{:,}".format(int(round(v / 100.0))) if v is not None else "-")]
    t1 = table(hd, rws, tuple(range(1, len(hd))))
    trend = ""
    vals = [(y, (dv.get("dps") or {}).get(y)) for y in ys]
    if len(vals) >= 2 and vals[0][1] and vals[1][1]:
        a, b = vals[0][1], vals[1][1]; trend = "<p class=\"lead\">주당 배당금은 %s년 %s원에서 %s년 %s원으로 %.1f%% %s했습니다.</p>" % (vals[1][0], num(b), vals[0][0], num(a), abs((a - b) / b * 100), sgn(a - b))
    ni = d["cur"].get("n")
    ex = ""
    if tot and ni and ni > 0: ex = "<p class=\"lead\">배당금 총액 %s은 당기순이익 %s의 %.1f%% 수준입니다.</p>" % (fw(tot * 1e6), fw(ni), tot * 1e6 / ni * 100)
    nb = ""
    if d["ind2"]:
        near = sorted([x for x in BY_IND[d["ind2"]] if x["yld"] and x is not d], key=lambda x: -x["yld"])[:8]
        if near: nb = '<h2 class="group-title">🏭 같은 업종 배당수익률 높은 기업</h2>' + table(["회사", "구분", "주당 배당금", "배당수익률"], [[comp_link(x), x["mk"], num(x["dps"]) + "원", pct(x["yld"], 2)] for x in near], (2, 3))
    body = f"""
<div class="page-head"><h1>{esc(d['n'])} 배당금·배당수익률 ({FY}년)</h1><p>{d['mk']} · {esc(d['indn'] or '기업')} · {ASOF}</p></div>
{lead}
{ad()}
<h2 class="group-title">💵 배당 추이</h2>
{t1}
{trend}{ex}
{nb}
<p class="note">배당 정보는 보통주 기준이며 우선주 배당은 별도입니다. 배당금은 이사회·주주총회 결의에 따라 달라지며 과거 배당이 미래 배당을 보장하지 않습니다. 배당소득세는 <a href="https://wooatax.wooahouse.com">우아세금</a>에서 확인하세요. {NOTE}</p>
{chips(sub_chips(d))}
{chips(rk("dividend", "배당 순위") + ind_chip(d))}
"""
    faq = []
    if cur: faq.append(("%s 주당 배당금은 얼마인가요?" % d["n"], "%s년 보통주 기준 주당 현금배당금은 %s원%s입니다." % (FY, num(cur), (", 현금배당수익률 %s" % pct(yl, 2)) if yl else "")))
    if pay: faq.append(("%s 배당성향은?" % d["n"], "%s년 현금배당성향은 %s입니다. 배당성향은 당기순이익 중 배당으로 지급한 비율입니다." % (FY, pct(pay, 1))))
    faq.append(("배당수익률은 어떻게 계산하나요?", "주당 배당금을 결산기말 주가로 나눈 값입니다. 사업보고서에 공시된 현금배당수익률을 그대로 사용했습니다."))
    desc = "%s %s년 주당 현금배당금 %s원, 현금배당수익률 %s, 배당성향 %s. 최근 배당 추이와 같은 업종 배당 기업 비교." % (d["n"], FY, num(cur), pct(yl, 2), pct(pay, 1))
    write(path, layout(path, "%s 배당금·배당수익률 (%s년)" % (d["n"], FY), desc, body, faq, crumbs_for(d, "배당", "dividend/"), extra_ld=org_ld(d)), "0.5")

# ───────────────────────── 최대주주 ─────────────────────────
def page_holder(d):
    h = d["hold"]; path = d["path"] + "shareholders/"
    top = h.get("top"); rt = h.get("rt"); al = h.get("all")
    parts = []
    if top: parts.append("최대주주는 <b>%s</b>%s" % (esc(top), (" (지분율 %s)" % pct(rt, 2)) if rt is not None else ""))
    if al is not None: parts.append("최대주주와 특수관계인을 합친 지분율은 <b>%s</b>" % pct(al, 2))
    lead = '<p class="lead"><b>%s</b>의 %s년 사업보고서 기준 %s입니다. 기준일은 결산기말이며 보통주 기준입니다.</p>' % (esc(d["n"]), FY, ", ".join(parts))
    rows = [["최대주주", esc(top or "-")], ["최대주주 지분율", pct(rt, 2)], ["최대주주 보유 주식 수", ("%s주" % num(h["sh"])) if h.get("sh") else "-"], ["최대주주·특수관계인 합계 지분율", pct(al, 2)]]
    if h.get("stlm"): rows.append(["기준일", esc(h["stlm"])])
    if al is not None: rows.append(["그 외 주주 지분율(추정)", pct(max(0, 100 - al), 2)])
    t1 = table(["항목", "내용"], rows)
    note2 = ""
    if al is not None: note2 = "<p class=\"lead\">최대주주 측 지분이 %s이므로 %s</p>" % (pct(al, 1), "경영권이 비교적 안정적인 편입니다." if al >= 50 else "지분이 분산되어 있어 경영권 변동 가능성에 유의가 필요합니다." if al < 30 else "과반에는 못 미치지만 의결권 영향력이 큰 구조입니다.")
    body = f"""
<div class="page-head"><h1>{esc(d['n'])} 최대주주·지분율 ({FY}년)</h1><p>{d['mk']} · {esc(d['indn'] or '기업')} · {ASOF}</p></div>
{lead}
{ad()}
<h2 class="group-title">🧾 주주 현황</h2>
{t1}
{note2}
<p class="note">개인 주주는 최대주주 본인에 한해 사업보고서에 공시된 대로 표기했습니다. 5% 이상 주주와 주식 수 변동은 DART 원문의 ‘주주에 관한 사항’을 확인하세요. {NOTE}</p>
{chips(sub_chips(d))}
{chips(ind_chip(d) or [("기업 검색", "/company/")])}
"""
    faq = [("%s 최대주주는 누구인가요?" % d["n"], "%s년 사업보고서 기준 최대주주는 %s%s입니다." % (FY, top or "공시되지 않음", (" (지분율 %s)" % pct(rt, 2)) if rt is not None else ""))]
    if al is not None: faq.append(("최대주주와 특수관계인 지분율은?", "합계 %s입니다. 특수관계인은 친족·계열회사·임원 등 최대주주와 특별한 관계에 있는 주주를 말합니다." % pct(al, 2)))
    desc = "%s 최대주주 %s%s, 최대주주·특수관계인 합계 지분율 %s (%s년 사업보고서 기준)." % (d["n"], top or "-", (" 지분율 %s" % pct(rt, 2)) if rt is not None else "", pct(al, 2), FY)
    write(path, layout(path, "%s 최대주주·지분율 (%s년)" % (d["n"], FY), desc, body, faq, crumbs_for(d, "최대주주", "shareholders/"), extra_ld=org_ld(d)), "0.5")

# ───────────────────────── 순위 ─────────────────────────
MARKETS = [("", "전체", None), ("kospi", "코스피", "Y"), ("kosdaq", "코스닥", "K")]
def rank_table(lst, m, n=100):
    second = "영업이익" if m[0] == "revenue" else "매출액"
    rows = [[str(i + 1), comp_link(d), d["mk"], esc(d["indn"] or "-"), m[3](d), fw(d["cur"].get("o")) if m[0] == "revenue" else fw(d["cur"].get("r"))] for i, d in enumerate(lst[:n])]
    return table(["순위", "회사", "구분", "업종", m[1], second], rows, (0, 4, 5))
def page_rank(m, mkslug, mklabel, mkcl):
    key, label, getter, fmt, rev, phrase = m
    pool = [d for d in DATA if (mkcl is None or d["cl"] == mkcl)]
    lst = [d for d in pool if getter(d) is not None]; lst.sort(key=lambda d: (-getter(d) if rev else getter(d), d["n"]))
    if len(lst) < 10: return
    path = "/rank/%s/%s" % (key, (mkslug + "/") if mkslug else "")
    pre = (mklabel + " ") if mkcl else ""
    top = lst[0]
    others = [(("%s %s" % (l2, label)) if s2 else "전체 " + label, "/rank/%s/%s" % (key, (s2 + "/") if s2 else "")) for s2, l2, _ in MARKETS if s2 != mkslug]
    body = f"""
<div class="page-head"><h1>{pre}{label} 순위 TOP 100 ({FY}년)</h1><p>{ASOF} · 사업보고서 제출 {num(len(pool))}개 기업 중</p></div>
<p class="lead">{FY}년 사업보고서 기준 {pre}{phrase} 기업 순위입니다. 1위는 <a href="{top['path']}">{esc(top['n'])}</a>({label} {fmt(top)})이며 100위까지 정리했습니다. 회사 이름을 누르면 재무제표·평균연봉·배당 정보를 볼 수 있습니다.</p>
{ad()}
{rank_table(lst, m)}
<p class="note">{NOTE}{' 영업이익률은 매출액 100억원 이상 기업만 비교했습니다.' if key == 'margin' else ''}{' 직원 1인 평균급여액은 사업보고서 공시 값입니다.' if key == 'salary' else ''}</p>
{chips(others)}
{chips([(x[1] + " 순위", "/rank/%s/" % x[0]) for x in METRICS if x[0] != key and HAS[x[0]]])}
"""
    faq = [("%s%s이(가) 가장 높은 기업은?" % (pre, label), "%s년 사업보고서 기준 %s%s 1위는 %s(%s)입니다." % (FY, pre, label, top["n"], fmt(top))),
           ("순위는 어떤 기준인가요?", "DART에 공시된 %s 사업보고서 값을 기준으로 하며 연결재무제표가 있으면 연결, 없으면 별도 값을 씁니다." % ASOF)]
    write(path, layout(path, "%s%s 순위 TOP 100 (%s년)" % (pre, label, FY), "%s년 사업보고서 기준 %s%s 기업 순위 TOP 100. 1위 %s(%s)." % (FY, pre, phrase, top["n"], fmt(top)), body, faq, [("홈", "/"), ("순위", "/rank/revenue/"), (pre + label, path)], coupang=(key in ("revenue", "salary", "dividend") and not mkcl)), "0.8" if not mkcl else "0.6")

# ───────────────────────── 업종 · 지역 ─────────────────────────
def sal_top_block(lst):
    top = sorted([d for d in lst if d["sal"]], key=lambda d: -d["sal"])[:10]
    if not top: return ""
    return '<h2 class="group-title">💰 평균급여 TOP 10</h2>' + table(["회사", "구분", "1인 평균급여", "직원 수"], [[comp_link(d), d["mk"], man(d["sal"]), num(d["empn"])] for d in top], (2, 3))

def page_industry(code):
    lst = sorted(BY_IND[code], key=lambda d: (-(d["cur"].get("r") or -1), d["n"])); path = "/industry/%s/" % code
    label = KSIC[code]; n = len(lst)
    rs = [d["cur"]["r"] for d in lst if d["cur"].get("r")]
    sm = med(lst, lambda x: x["sal"]); mg = med(lst, lambda x: x["margin"]); db = med(lst, lambda x: x["debt"])
    stats = []
    if rs: stats.append("매출 합계 %s" % fw(sum(rs)))
    if sm: stats.append("1인 평균급여 중앙값 %s" % man(sm))
    if mg is not None: stats.append("영업이익률 중앙값 %s" % pct(mg))
    if db is not None: stats.append("부채비율 중앙값 %s" % pct(db, 0))
    body = f"""
<div class="page-head"><h1>{esc(label)} 기업 {n}곳 — 매출·평균연봉 비교 ({FY}년)</h1><p>표준산업분류 {code} · {ASOF}</p></div>
<p class="lead"><b>{esc(label)}</b>(표준산업분류 {code})에서 {FY}년 사업보고서를 제출한 기업은 {n}곳입니다. {', '.join(stats)}입니다. 매출액이 큰 순서로 최대 200곳을 표시했습니다.</p>
{ad()}
<h2 class="group-title">🏆 매출액 순</h2>
{table(H_COMP, rows_basic(lst[:200]), (3, 4))}
{sal_top_block(lst)}
<p class="note">{NOTE}</p>
{chips([("업종 전체", "/industry/"), ("매출 순위", "/rank/revenue/"), ("평균연봉 순위", "/rank/salary/")])}
"""
    faq = [("%s 기업은 몇 곳인가요?" % label, "DART %s년 사업보고서를 제출한 기업 중 %s곳이 이 업종으로 분류됩니다." % (FY, n)), ("업종은 어떻게 분류했나요?", "DART 기업개황의 업종코드(표준산업분류) 앞 2자리 중분류 기준입니다.")]
    write(path, layout(path, "%s 기업 %d곳 — 매출·평균연봉·영업이익 비교 (%s년)" % (label, n, FY), "%s 사업보고서 제출 기업 %d곳의 매출·영업이익·평균연봉. %s." % (label, n, ", ".join(stats[:3])), body, faq, [("홈", "/"), ("업종별", "/industry/"), (label, path)]), "0.7")

def hub_industry():
    codes = sorted(BY_IND, key=lambda c: -len(BY_IND[c]))
    rows = [['<a href="/industry/%s/">%s</a>' % (c, esc(KSIC[c])), len(BY_IND[c]), fw(sum(d["cur"].get("r") or 0 for d in BY_IND[c])), man(med(BY_IND[c], lambda x: x["sal"]))] for c in codes]
    body = f"""
<div class="page-head"><h1>업종별 기업 — 매출·평균연봉 비교 ({FY}년)</h1><p>표준산업분류 중분류 · {ASOF}</p></div>
<p class="lead">사업보고서를 제출한 {num(len(DATA))}개 기업을 {len(codes)}개 업종으로 나눴습니다. 업종을 누르면 매출 순위와 평균연봉 TOP 10, 업종 중앙값을 볼 수 있습니다.</p>
{ad()}
{table(['업종', '기업 수', '매출 합계', '평균급여 중앙값'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("매출 순위", "/rank/revenue/"), ("평균연봉 순위", "/rank/salary/"), ("지역별", "/region/")])}
"""
    write("/industry/", layout("/industry/", "업종별 기업 — 매출·평균연봉·영업이익 비교 (%s년)" % FY, "사업보고서 제출 %s개 기업을 %d개 업종으로 분류. 업종별 매출 합계와 평균급여 중앙값." % (num(len(DATA)), len(codes)), body,
                              [("업종은 어떻게 분류했나요?", "DART 기업개황의 업종코드(표준산업분류) 앞 2자리 중분류 기준입니다.")], [("홈", "/"), ("업종별", "/industry/")], coupang=True), "0.8")

def page_region(sido):
    lst = sorted(BY_SIDO[sido], key=lambda d: (-(d["cur"].get("r") or -1), d["n"])); path = "/region/%s/" % sido; full = SIDO_FULL[sido]
    sm = med(lst, lambda x: x["sal"]); n = len(lst)
    inds = collections.Counter(d["indn"] for d in lst if d["indn"]).most_common(5)
    body = f"""
<div class="page-head"><h1>{full} 본사 기업 {n}곳 — 매출·평균연봉 ({FY}년)</h1><p>사업보고서 제출 기업 · {ASOF}</p></div>
<p class="lead">본사 주소가 <b>{full}</b>인 사업보고서 제출 기업은 {n}곳입니다. 업종은 {', '.join('%s %d곳' % (a, b) for a, b in inds)} 순으로 많고, 1인 평균급여 중앙값은 {man(sm)}입니다. 매출액이 큰 순서로 최대 200곳을 표시했습니다.</p>
{ad()}
{table(H_COMP, rows_basic(lst[:200]), (3, 4))}
{sal_top_block(lst)}
<p class="note">{NOTE} 지역은 DART 기업개황의 본사 주소 기준입니다.</p>
{chips([("지역 전체", "/region/"), ("업종별", "/industry/"), ("매출 순위", "/rank/revenue/")])}
"""
    faq = [("%s에 본사를 둔 공시 기업은 몇 곳인가요?" % full, "DART %s년 사업보고서 제출 기업 중 %s곳입니다." % (FY, n))]
    write(path, layout(path, "%s 본사 기업 %d곳 — 매출·평균연봉 (%s년)" % (full, n, FY), "%s에 본사를 둔 사업보고서 제출 기업 %d곳의 매출·영업이익·평균연봉. 평균급여 중앙값 %s." % (full, n, man(sm)), body, faq, [("홈", "/"), ("지역별", "/region/"), (full, path)]), "0.7")

def hub_region():
    rows = [['<a href="/region/%s/">%s</a>' % (s, SIDO_FULL[s]), len(BY_SIDO[s]), fw(sum(d["cur"].get("r") or 0 for d in BY_SIDO[s])), man(med(BY_SIDO[s], lambda x: x["sal"]))] for s in SIDOS]
    body = f"""
<div class="page-head"><h1>지역별 기업 — 본사 소재지별 매출·평균연봉 ({FY}년)</h1><p>사업보고서 제출 기업 · {ASOF}</p></div>
<p class="lead">사업보고서를 제출한 기업을 본사 소재지(시도)별로 정리했습니다. 지역을 누르면 해당 지역 기업의 매출 순위와 평균급여 TOP 10을 볼 수 있습니다.</p>
{ad()}
{table(['시도', '기업 수', '매출 합계', '평균급여 중앙값'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("업종별", "/industry/"), ("매출 순위", "/rank/revenue/")])}
"""
    write("/region/", layout("/region/", "지역별 기업 — 본사 소재지별 매출·평균연봉 (%s년)" % FY, "사업보고서 제출 기업을 본사 소재지 시도별로 정리. 지역별 매출 합계와 평균급여 중앙값.", body, None, [("홈", "/"), ("지역별", "/region/")], coupang=True), "0.7")

# ───────────────────────── 기업 목록(초성) · 검색 ─────────────────────────
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
GROUP = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}
def cho(name):
    s = re.sub(r"^(\(주\)|㈜|주식회사)\s*", "", name)
    for ch in s:
        if "가" <= ch <= "힣":
            c = CHO[(ord(ch) - 0xAC00) // 588]; return GROUP.get(c, c)
        if ch.isalpha() and ch.isascii(): return "A-Z"
        if ch.isdigit(): return "0-9"
    return "기타"
BY_CHO = collections.defaultdict(list)
for d in DATA: BY_CHO[cho(d["n"])].append(d)
CHO_ORDER = [c for c in "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"] + ["A-Z", "0-9", "기타"]
CHO_SLUG = {c: ("az" if c == "A-Z" else "09" if c == "0-9" else "etc" if c == "기타" else c) for c in CHO_ORDER}

def page_list(c):
    lst = sorted(BY_CHO[c], key=lambda d: d["n"]); path = "/company/list/%s/" % CHO_SLUG[c]
    body = f"""
<div class="page-head"><h1>{c} 으로 시작하는 기업 {len(lst)}곳</h1><p>사업보고서 제출 기업 · {ASOF}</p></div>
<p class="lead">회사 이름이 <b>{c}</b>(으)로 시작하는 사업보고서 제출 기업 {len(lst)}곳입니다. 이름을 누르면 매출·영업이익·평균연봉·배당 정보를 볼 수 있습니다.</p>
{ad()}
{table(H_COMP, rows_basic(lst), (3, 4))}
<p class="note">{NOTE}</p>
{chips([(x, "/company/list/%s/" % CHO_SLUG[x]) for x in CHO_ORDER if x in BY_CHO and x != c])}
"""
    write(path, layout(path, "%s 으로 시작하는 기업 %d곳 — 매출·영업이익" % (c, len(lst)), "회사 이름이 %s(으)로 시작하는 사업보고서 제출 기업 %d곳 목록과 매출·영업이익." % (c, len(lst)), body, None, [("홈", "/"), ("기업", "/company/"), (c, path)]), "0.5")

def page_company_hub():
    top10 = sorted(DATA, key=lambda d: -(d["cur"].get("r") or 0))[:10]
    t_top = table(["순위", "회사", "구분", "업종", "매출액", "영업이익"], [[str(i + 1)] + r for i, r in enumerate(rows_basic(top10))], (0, 4, 5))
    body = f"""
<div class="page-head"><h1>기업 검색 — 매출·평균연봉·배당 ({FY}년)</h1><p>사업보고서 제출 {num(len(DATA))}개 기업 · {ASOF}</p></div>
<p class="lead">회사 이름을 입력하면 매출액·영업이익, 직원 평균급여, 배당금, 최대주주 정보를 볼 수 있습니다. 이름 첫 글자(초성)로 찾을 수도 있습니다.</p>
<div class="search-box"><input id="q" type="search" placeholder="회사 이름 (예: 삼성전자)" autocomplete="off" aria-label="회사 이름 검색"><div id="res" class="search-res"></div></div>
{ad()}
<h2 class="group-title">🔤 이름으로 찾기</h2>
{chips([("%s (%d)" % (c, len(BY_CHO[c])), "/company/list/%s/" % CHO_SLUG[c]) for c in CHO_ORDER if c in BY_CHO])}
<h2 class="group-title">🏆 매출액 TOP 10</h2>
{t_top}
<p class="note">{NOTE}</p>
{chips([("업종별", "/industry/"), ("지역별", "/region/"), ("매출 순위", "/rank/revenue/")])}
<script>
(function(){{var q=document.getElementById('q'),res=document.getElementById('res'),idx=null,busy=false;
function load(cb){{if(idx)return cb();if(busy)return;busy=true;fetch('/assets/search-index.json').then(function(r){{return r.json()}}).then(function(j){{idx=j;busy=false;cb()}});}}
function esc(s){{return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}}
function go(){{var v=q.value.trim().toLowerCase();if(!v){{res.innerHTML='';return}}load(function(){{var out=[];for(var i=0;i<idx.length&&out.length<30;i++){{if(idx[i][0].toLowerCase().indexOf(v)>-1)out.push(idx[i])}}
res.innerHTML=out.length?out.map(function(x){{return '<a href="'+x[1]+'">'+esc(x[0])+' <span>'+x[2]+'</span></a>'}}).join(''):'<p>검색 결과가 없습니다.</p>';}});}}
q.addEventListener('input',go);}})();
</script>
"""
    write("/company/", layout("/company/", "기업 검색 — 매출·평균연봉·배당 (%s년)" % FY, "사업보고서 제출 %s개 기업의 매출액·영업이익·평균연봉·배당금·최대주주를 이름으로 검색하세요." % num(len(DATA)), body, None, [("홈", "/"), ("기업", "/company/")]), "0.9")

# ───────────────────────── 홈 · 소개 · 개인정보 ─────────────────────────
def mini_rank(key, n=5):
    m = MET[key]; lst = sorted([d for d in DATA if m[2](d) is not None], key=lambda d: (-m[2](d) if m[4] else m[2](d), d["n"]))[:n]
    return table(["순위", "회사", m[1]], [[str(i + 1), comp_link(d), m[3](d)] for i, d in enumerate(lst)], (0, 2))
def page_home():
    body = f"""
<div class="hero"><h1>🏢 기업 {num(len(DATA))}곳 — 매출·평균연봉·배당 한눈에</h1><p>DART 사업보고서({FY}년)를 기업별로 정리했습니다.</p></div>
{ad()}
<div class="card-grid">
<a class="card" href="/company/"><b>🔍 기업 검색</b><span>이름으로 바로 찾기</span></a>
<a class="card" href="/rank/revenue/"><b>🏆 매출 순위</b><span>전체·코스피·코스닥</span></a>
<a class="card" href="/rank/salary/"><b>💰 평균연봉 순위</b><span>직원 1인 평균급여</span></a>
<a class="card" href="/rank/dividend/"><b>💵 배당 순위</b><span>현금배당수익률</span></a>
<a class="card" href="/industry/"><b>🏭 업종별</b><span>{len(BY_IND)}개 업종 비교</span></a>
<a class="card" href="/region/"><b>📍 지역별</b><span>본사 소재지별</span></a>
</div>
<h2 class="group-title">🏆 매출액 TOP 5</h2>{mini_rank('revenue')}
<h2 class="group-title">💰 1인 평균급여 TOP 5</h2>{mini_rank('salary')}
<h2 class="group-title">💵 배당수익률 TOP 5</h2>{mini_rank('dividend')}
<p class="lead">우아기업은 금융감독원 전자공시시스템(DART) 오픈API가 제공하는 {ASOF} 사업보고서를 기업별로 정리한 사이트입니다. 사업보고서를 제출한 {num(len(DATA))}개 기업의 매출액·영업이익·당기순이익, 부채비율, 직원 수와 1인 평균급여, 주당 배당금과 배당수익률, 최대주주 지분율을 확인할 수 있습니다. 자세한 기준은 <a href="/about/">데이터 설명</a>을 참고하세요.</p>
"""
    faq = [("어떤 기업이 들어 있나요?", "DART에 %s년 사업보고서를 제출한 상장(코스피·코스닥·코넥스) 및 일부 비상장 공시 기업 %s곳입니다." % (FY, num(len(DATA)))), ("재무 정보는 최신인가요?", "%s 사업보고서 기준이며 이후 분기·반기 실적과 정정공시는 반영되지 않았습니다." % ASOF)]
    write("/", layout("/", "우아기업 — 기업 %s곳 매출·평균연봉·배당·최대주주 (%s년)" % (num(len(DATA)), FY), "DART 사업보고서 기반 기업 %s곳의 매출·영업이익, 직원 평균급여, 배당금, 최대주주를 기업별로 정리했습니다." % num(len(DATA)), body, faq), "1.0")

def page_about():
    body = f"""
<div class="page-head"><h1>데이터 설명</h1><p>정보의 출처와 한계</p></div>
<h2 class="group-title">📚 출처</h2><p class="lead">금융감독원 전자공시시스템(DART) 오픈API(opendart.fss.or.kr)가 제공하는 {ASOF} 정기보고서(사업보고서) 정보를 사용했습니다. 기업개황, 주요계정 재무정보(매출액·영업이익·당기순이익·자산·부채·자본), 직원 현황(직원 수·1인 평균급여액·평균 근속연수), 배당에 관한 사항(주당 현금배당금·수익률·성향), 최대주주 현황, 이사·감사 전체의 보수 현황을 반영했습니다.</p>
<h2 class="group-title">🧮 계산 방법</h2><p class="lead">부채비율은 부채총계를 자본총계로 나눈 값, 영업이익률은 영업이익을 매출액으로 나눈 값입니다. 연결재무제표가 있는 기업은 연결, 없으면 별도 기준이며 금융업처럼 매출액이 없는 업종은 해당 항목이 비어 있을 수 있습니다. 업종은 DART 기업개황 업종코드의 앞 2자리(표준산업분류 중분류)로 묶었고 지역은 본사 주소의 시도 기준입니다.</p>
<h2 class="group-title">⚠️ 한계</h2><p class="lead">사업보고서를 제출한 기업만 포함되며 모든 법인을 포함하지 않습니다. 정정공시, 분기·반기 실적, 기준일 이후의 변동은 반영되지 않습니다. 평균급여는 사업보고서에 공시된 값이며 직원 개인의 연봉과 다를 수 있습니다. 이 사이트는 투자 권유나 신용평가를 제공하지 않으며 의사결정 전에 DART 원문을 확인해야 합니다.</p>
<h2 class="group-title">📬 문의·정정</h2><p class="lead">오류 제보나 정정·삭제 요청은 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요.</p>
"""
    write("/about/", layout("/about/", "데이터 설명 — 출처와 한계", "우아기업 데이터 출처(금융감독원 DART 오픈API 사업보고서)와 계산 방법, 한계를 공개합니다.", body, None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.5")

def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아기업(wooacorp.wooahouse.com, 이하 “서비스”)은 회원가입·로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다.</p>
<h3>자동 수집 정보</h3><p class="lead">서비스 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>공시 정보의 정정·삭제</h3><p class="lead">서비스에 게시된 기업 정보는 금융감독원 DART에 공시된 자료이며, 오류 정정이나 삭제 요청은 아래 연락처로 보내 주세요.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 26일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아기업 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try: from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    im = Image.new("RGB", (1200, 630), (30, 64, 175)); dr = ImageDraw.Draw(im)
    def font(sz):
        for n in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아기업", font=font(110), fill=(30, 58, 138))
    dr.text((150, 310), "매출 · 평균연봉 · 배당 · 최대주주", font=font(54), fill=(31, 41, 55))
    dr.text((150, 390), "DART 사업보고서 기업별 정리", font=font(54), fill=(31, 41, 55))
    dr.text((150, 480), "wooacorp.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

def main():
    t0 = time.time(); make_og()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    for nf in ROOT.glob("naver*.html"): shutil.copy(nf, OUT / nf.name)
    (OUT / "assets" / "search-index.json").write_text(json.dumps([[d["n"], d["path"], d["mk"]] for d in sorted(DATA, key=lambda d: d["n"])], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for d in DATA:
        page_company(d)
        if d.get("emp") and (d["empn"] or d["sal"]): page_salary(d)
        if d["dps"]: page_dividend(d)
        if d.get("hold") and d["hold"].get("top"): page_holder(d)
    for m in METRICS:
        for s2, l2, c2 in MARKETS: page_rank(m, s2, l2, c2)
    for c in sorted(BY_IND): page_industry(c)
    hub_industry()
    for s in SIDOS: page_region(s)
    hub_region()
    for c in BY_CHO: page_list(c)
    page_company_hub(); page_home(); page_about(); page_privacy()
    today = time.strftime("%Y-%m-%d")
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr_) for p, pr_ in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooacorp.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/company/">기업 검색</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
