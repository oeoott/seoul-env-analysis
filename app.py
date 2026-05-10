import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="서울시 환경-교통 대시보드", layout="wide")

# DB 연결 함수
def run_query(query):
    conn = sqlite3.connect('./seoul_env.db')
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return df

# 헤더 부분
st.title("🏙️ 서울시 환경 및 교통 데이터 통합 분석 대시보드")
st.markdown("""
본 대시보드는 서울시의 **공원 면적, 미세먼지 농도, 따릉이 이용 현황** 데이터를 결합하여 
환경 지표와 시민들의 이동 패턴 사이의 상관관계를 분석합니다.
""")

# --- 분석 1: 인당 공원 면적 vs 미세먼지 농도 (Scatter Plot) ---
st.header("1. 자치구별 녹지 인프라와 공기질의 상관관계")

query1 = """
SELECT 
    p.자치구, 
    p.인당공원면적, 
    AVG(a.미세먼지) as 평균미세먼지
FROM park p
JOIN air a ON p.자치구 = a.자치구
GROUP BY p.자치구
"""

df1 = run_query(query1)

col1_chart, col1_desc = st.columns([2, 1])

with col1_chart:
    fig1 = px.scatter(df1, x="인당공원면적", y="평균미세먼지", 
                 text="자치구", size="인당공원면적", color="평균미세먼지",
                 title="자치구별 인당 공원 면적 대비 평균 미세먼지",
                 labels={"인당공원면적": "1인당 공원 면적 (㎡)", "평균미세먼지": "평균 미세먼지 농도 (㎍/㎥)"},
                 color_continuous_scale=px.colors.sequential.Viridis)
    st.plotly_chart(fig1, use_container_width=True)

with col1_desc:
    st.subheader("SQL Query")
    st.code(query1, language='sql')
    st.subheader("Business Insight")
    st.info("""
    - 인당 공원 면적이 넓은 자치구일수록 평균 미세먼지 농도가 낮게 형성되는 경향이 있는지 확인합니다.
    - 녹지 조성 정책이 실제 대기질 개선에 기여하는 정량적 근거로 활용 가능합니다.
    - 데이터 상 이탈치(Outlier)가 있는 구는 공업 지역이나 교통 밀집 지역 등 외부 요인 분석이 추가로 필요합니다.
    """)

st.divider()

# --- 분석 2: 미세먼지 수준별 따릉이 대여량 비교 (Bar Chart) ---
st.header("2. 미세먼지 농도에 따른 따릉이 이용 변화")

query2 = """
WITH AirQuality AS (
    SELECT 자치구, AVG(미세먼지) as avg_pm10
    FROM air
    GROUP BY 자치구
),
Threshold AS (
    SELECT AVG(avg_pm10) as total_avg FROM AirQuality
)
SELECT 
    CASE WHEN a.avg_pm10 >= t.total_avg THEN '미세먼지 높음' ELSE '미세먼지 낮음' END as 대기질상태,
    AVG(b.대여건수) as 평균대여건수
FROM AirQuality a
JOIN bike b ON a.자치구 = b.자치구
CROSS JOIN Threshold t
GROUP BY 대기질상태
"""

df2 = run_query(query2)

col2_chart, col2_desc = st.columns([2, 1])

with col2_chart:
    fig2 = px.bar(df2, x="대기질상태", y="평균대여건수", 
             color="대기질상태",
             title="대기질 수준별 평균 자전거 대여량 비교",
             color_discrete_map={'미세먼지 높음': '#EF553B', '미세먼지 낮음': '#636EFA'})
    st.plotly_chart(fig2, use_container_width=True)

with col2_desc:
    st.subheader("SQL Query")
    st.code(query2, language='sql')
    st.subheader("Business Insight")
    st.info("""
    - 대기질 상태가 '좋음/보통'인 지역에서 자전거 이용률이 상대적으로 높게 나타나는지 비교합니다.
    - 미세먼지 주의보 발령 시 따릉이 이용객 감소 폭을 예측하여 운영 효율화에 기여할 수 있습니다.
    - 환경 요인이 시민들의 친환경 교통수단 선택에 미치는 심리적 저항선을 파악합니다.
    """)

st.divider()

# --- 분석 3: 공원 면적 대비 자전거 이용 활성화 정도 (Bubble Chart) ---
st.header("3. 자치구별 공원 인프라 기반 자전거 이용 활성화도")

query3 = """
SELECT 
    p.자치구, 
    p.공원면적, 
    SUM(b.대여건수 + b.반납건수) as 총이용량,
    (SUM(b.대여건수 + b.반납건수) / p.공원면적) as 면적대비이용효율
FROM park p
JOIN bike b ON p.자치구 = b.자치구
GROUP BY p.자치구
ORDER BY 총이용량 DESC
"""

df3 = run_query(query3)

col3_chart, col3_desc = st.columns([2, 1])

with col3_chart:
    fig3 = px.scatter(df3, x="공원면적", y="총이용량",
                 size="면적대비이용효율", color="자치구",
                 title="공원 면적 대비 자전거 이용량 (버블 크기: 이용 효율)",
                 labels={"공원면적": "공원 전체 면적 (㎡)", "총이용량": "자전거 총 대여/반납 건수"})
    st.plotly_chart(fig3, use_container_width=True)

with col3_desc:
    st.subheader("SQL Query")
    st.code(query3, language='sql')
    st.subheader("Business Insight")
    st.info("""
    - 공원 면적이 넓음에도 자전거 이용량이 적은 구는 연계 자전거 도로 확충이 필요한 잠재 지역입니다.
    - 버블 크기가 큰 지역은 공원 인프라를 시민들이 이동 및 레저 목적으로 매우 효율적으로 사용 중임을 나타냅니다.
    - 향후 신규 따릉이 대여소 설치 시 '면적 대비 이용 효율'이 높은 지역을 우선 고려할 수 있습니다.
    """)

st.sidebar.info("데이터 출처: 서울시 공공데이터 포털 기반 가상 DB")
