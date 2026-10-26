# 우아기업 (wooacorp.wooahouse.com)

금융감독원 DART OpenDART API의 사업보고서(FY2024) 제출 기업을 기업별로 정리한 정적 사이트.

- 기업 메인(재무 5개년) · 평균연봉 · 배당 · 최대주주 페이지, 지표별 순위(전체·코스피·코스닥), 업종(표준산업분류 중분류)·지역·초성 목록
- 빌드: `python scripts/build_site.py` (입력 `data/companies.json.gz`, GitHub Actions에서도 동일)
- 데이터 갱신(로컬): `_newdata/dart_list.py` → `_newdata/dart_fetch.py`(키 `_newdata/dart.env`, 저장소 밖) → `python scripts/build_data.py`
- 개인 이름은 최대주주 본인만 표기, 임원 개인정보는 수집하지 않음
