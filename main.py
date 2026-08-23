import os
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="연령별 인구 구조", layout="wide")

DATA_FILENAME = "202607_202607_연령별인구현황_월간.csv"
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILENAME)


# -----------------------------
# 데이터 불러오기 & 전처리
# -----------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949", low_memory=False)
    # 콤마 제거 후 숫자형 변환 (첫 컬럼=행정구역 제외)
    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def parse_age_columns(columns, gender_key: str):
    """'YYYY년MM월_성별_N세' 또는 'YYYY년MM월_성별_100세 이상' 컬럼에서
    (age:int, colname) 목록을 추출"""
    result = []
    for col in columns:
        m = re.match(rf"^\d{{4}}년\d{{2}}월_{gender_key}_(\d+)세$", col)
        if m:
            result.append((int(m.group(1)), col))
            continue
        m2 = re.match(rf"^\d{{4}}년\d{{2}}월_{gender_key}_100세 이상$", col)
        if m2:
            result.append((100, col))
    result.sort(key=lambda x: x[0])
    return result


def clean_region_name(raw: str) -> str:
    """'서울특별시 종로구 청운효자동(1111051500)' -> '서울특별시 종로구 청운효자동'"""
    return re.sub(r"\s*\(\d+\)\s*$", "", str(raw)).strip()


st.title("📊 지역별 연령대 인구 구조")
st.caption("행정안전부 '연령별 인구현황' 월간 CSV 기반 시각화")

# -----------------------------
# 데이터 로드 (앱과 같은 폴더의 CSV를 자동으로 읽음)
# -----------------------------
if not os.path.exists(DATA_PATH):
    st.error(
        f"'{DATA_FILENAME}' 파일을 찾을 수 없습니다. "
        "app.py와 같은 폴더에 해당 CSV 파일을 함께 업로드(커밋)해주세요."
    )
    st.stop()

df = load_data(DATA_PATH)
df["_지역명"] = df["행정구역"].apply(clean_region_name)

# -----------------------------
# 지역 선택: 검색어 입력 + 드롭다운 선택
# -----------------------------
st.subheader("지역 선택")

col_search, col_select = st.columns([1, 2])

with col_search:
    keyword = st.text_input("지역명 검색 (예: 종로구, 해운대)", value="")

if keyword.strip():
    filtered_regions = df.loc[
        df["_지역명"].str.contains(keyword.strip(), case=False, na=False), "_지역명"
    ].tolist()
else:
    filtered_regions = df["_지역명"].tolist()

with col_select:
    selected_regions = st.multiselect(
        "지역 선택 (여러 지역 비교 가능)",
        options=filtered_regions,
        default=filtered_regions[:1] if filtered_regions else [],
    )

if not selected_regions:
    st.warning("최소 한 개 이상의 지역을 선택해주세요.")
    st.stop()

# -----------------------------
# 성별 선택
# -----------------------------
gender_map = {"전체": "계", "남자": "남", "여자": "여"}
gender_label = st.radio("성별", list(gender_map.keys()), horizontal=True)
gender_key = gender_map[gender_label]

# -----------------------------
# 그래프 (Plotly 꺾은선)
# -----------------------------
age_cols = parse_age_columns(df.columns, gender_key)

if not age_cols:
    st.error("연령별 컬럼을 찾지 못했습니다. CSV 형식을 확인해주세요.")
    st.stop()

fig = go.Figure()

for region in selected_regions:
    row = df.loc[df["_지역명"] == region]
    if row.empty:
        continue
    row = row.iloc[0]
    ages = [age for age, _ in age_cols]
    values = [row[col] for _, col in age_cols]
    fig.add_trace(
        go.Scatter(
            x=ages,
            y=values,
            mode="lines",
            name=region,
            line=dict(width=2),
        )
    )

fig.update_layout(
    title=f"연령별 인구 구조 ({gender_label})",
    xaxis_title="연령",
    yaxis_title="인구수",
    hovermode="x unified",
    legend_title="지역",
    height=550,
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 원본 데이터 표
# -----------------------------
with st.expander("선택 지역 원본 데이터 보기"):
    show_cols = ["_지역명"] + [c for _, c in age_cols]
    st.dataframe(
        df.loc[df["_지역명"].isin(selected_regions), show_cols].rename(
            columns={"_지역명": "지역"}
        )
    )
