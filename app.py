import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="서울시 환경-교통 분석 대시보드", layout="wide")

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect('./seoul_env.db')

def run_query(q):
    with get_connection() as conn:
        return pd.read_sql(q, conn)

st.title("🏙️ 서울시 환경 및 교통 데이터 분석 대시보드")
st.markdown("공원 면적, 미세먼지 농도, 그리고 따릉이 이용량 간의 상관관계를 분석합니다.")

# --- 1. 자치구별 1인당 공원 면적과 미세먼지 농도의 상관관계 ---
st.header("1. 공원 면적과 미세먼지의 상관관계")

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

col1_1, col1_2 = st.columns([2, 1])

with col1_1:
    fig1 = px.scatter(df1, x="인당공원면적", y="평균미세먼지", text="자치구", 
                     trendline="ols", title="자치구별 인당 공원 면적 vs 미세먼지 농도")
    st.plotly_chart(fig1, use_container_width=True)

with col1_2:
    st.subheader("SQL Query")
    st.code(query1, language='sql')
    st.subheader("💡 인사이트")
    st.write("""
    - 인당 공원 면적이 넓은 자치구일수록 평균 미세먼지 농도가 낮게 형성되는 음의 상관관계가 관찰됩니다.
    - 녹지 공간이 대기질 정화에 긍정적인 영향을 미칠 수 있음을 시사하며, 환경 정책 수립 시 녹지 확보의 중요성을 뒷받침합니다.
    - 특정 자치구가 추세선에서 크게 벗어날 경우, 공원 외의 다른 대기 오염 요인(교통량, 공업지대 등)을 추가 분석할 필요가 있습니다.
    """)

st.divider()

# --- 2. 미세먼지 수치에 따른 따릉이 대여량 비교 ---
st.header("2. 미세먼지 농도 그룹별 따릉이 이용 패턴")

query2 = """
WITH AirRank AS (
    SELECT 자치구, AVG(미세먼지) as avg_pm
    FROM air
    GROUP BY 자치구
),
MedianPM AS (
    SELECT AVG(avg_pm) as threshold FROM AirRank
)
SELECT 
    CASE WHEN r.avg_pm > m.threshold THEN '미세먼지 높음(상위 50%)' 
         ELSE '미세먼지 낮음(하위 50%)' END as 미세먼지구분,
    AVG(b_sum.total_rentals) as 평균대여량
FROM AirRank r
CROSS JOIN MedianPM m
JOIN (
    SELECT 자치구, SUM(대여건수) as total_rentals 
    FROM bike 
    GROUP BY 자치구
) b_sum ON r.자치구 = b_sum.자치구
GROUP BY 미세먼지구분
"""

df2 = run_query(query2)

col2_1, col2_2 = st.columns([2, 1])

with col2_1:
    fig2 = px.bar(df2, x="미세먼지구분", y="평균대여량", color="미세먼지구분",
                 title="대기질 수준에 따른 자치구별 평균 따릉이 대여량 비교",
                 color_discrete_map={'미세먼지 높음(상위 50%)': '#EF553B', '미세먼지 낮음(하위 50%)': '#636EFA'})
    st.plotly_chart(fig2, use_container_width=True)

with col2_2:
    st.subheader("SQL Query")
    st.code(query2, language='sql')
    st.subheader("💡 인사이트")
    st.write("""
    - 미세먼지 농도가 낮은 자치구 그룹의 따릉이 평균 대여량이 높은 그룹에 비해 상대적으로 많은 경향을 보입니다.
    - 이는 시민들이 대기질이 좋은 지역에서 야외 활동인 자전거 이용을 더 선호한다는 점을 보여줍니다.
    - 대기질이 나쁜 지역에서는 따릉이 이용 활성화를 위해 마스크 배부나 공기 정화 쉼터 설치 등 차별화된 전략이 필요할 수 있습니다.
    """)

st.divider()

# --- 3. 공원 면적 대비 자전거 이용 활성화 정도 (버블 차트) ---
st.header("3. 자치구별 녹지 인프라 및 자전거 이용 활성화")

query3 = """
SELECT 
    p.자치구, 
    p.공원면적, 
    SUM(b.대여건수) as 총대여건수,
    p.인당공원면적
FROM park p
JOIN bike b ON p.자치구 = b.자치구
GROUP BY p.자치구
"""

df3 = run_query(query3)

col3_1, col3_2 = st.columns([2, 1])

with col3_1:
    fig3 = px.scatter(df3, x="공원면적", y="총대여건수", size="인당공원면적", color="자치구",
                     title="공원 면적 vs 따릉이 대여량 (버블 크기: 인당 공원 면적)")
    st.plotly_chart(fig3, use_container_width=True)

with col3_2:
    st.subheader("SQL Query")
    st.code(query3, language='sql')
    st.subheader("💡 인사이트")
    st.write("""
    - 공원 면적이 넓고 인당 공원 면적(버블 크기)이 큰 자치구일수록 자전거 대여량이 활발한 '친환경 거점'으로서의 특징을 보입니다.
    - 대여량이 공원 면적에 비해 유난히 높은 지역은 공원 외에도 업무지구나 역세권 등 교통 수요가 결합된 지역일 가능성이 높습니다.
    - 녹지 면적은 넓으나 자전거 이용이 저조한 지역은 자전거 도로 정비나 대여소 추가 배치를 통해 인프라 효율성을 높일 수 있습니다.
    """)