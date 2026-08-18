# Cup with Handle 패턴 주식 스크리너 (Streamlit)

이 프로젝트는 전설적인 성장주 투자자 **윌리엄 오닐(William O'Neal)**의 **Cup with Handle (컵앤핸들) 패턴**을 실시간 데이터 기반으로 탐색하고 분석할 수 있는 웹 대시보드 애플리케이션입니다. 

한국 시장(KOSPI, KOSDAQ) 및 미국 시장(S&P 500, NASDAQ 100)의 종목을 대상으로 컵앤핸들 패턴 돌파 요건 및 거래량 급증 조건을 충족하는 종목을 발굴합니다.

## 📌 주요 기능
1. **다양한 대상 시장 제공**: 코스피(KOSPI), 코스닥(KOSDAQ), S&P 500(US), NASDAQ 100(US) 시장 실시간 데이터 분석 지원
2. **세부 스크리닝 조건 커스터마이징**:
   * **컵(Cup) 설정**: 이전 상승세 비율, 최소/최대 컵 기간, 최대 컵 깊이
   * **핸들(Handle) 설정**: 최소/최대 핸들 기간, 최대 핸들 깊이
   * **돌파(Breakout) 설정**: 최근 20일 평균 거래량 대비 돌파일 거래량 비율
3. **인터랙티브 분석 차트**: 포착된 종목에 대해 컵앤핸들 패턴의 핵심 지점(A, B, C, D, 돌파 지점) 및 거래량, 이동평균선을 시각화한 차트 제공
4. **데이터 내보내기**: 스크리닝 결과를 깔끔하게 정리된 Excel 파일(`.xlsx`)로 직접 다운로드 가능

## 🛠 설치 및 실행 방법

### 1. 요구사항
이 프로젝트는 Python 3.8 이상을 권장합니다.

### 2. 저장소 복제 및 의존성 설치
저장소를 로컬에 복제하고 필요한 패키지들을 설치합니다.

```bash
# 저장소 복제
git clone https://github.com/sonosgg-debug/streamlit-02-CupHandle.git
cd streamlit-02-CupHandle

# 필요한 패키지 설치
pip install -r requirements.txt
```

### 3. Streamlit 실행
설치가 완료되면 아래 명령어로 애플리케이션을 실행할 수 있습니다.

```bash
streamlit run app.py
```
명령어를 실행하면 웹 브라우저 창이 자동으로 열리며, 로컬 환경(`http://localhost:8501`)에서 접속하실 수 있습니다.

## 📂 파일 구조
* `app.py`: Streamlit 대시보드 UI 구성 및 전체 흐름 제어 메인 소스
* `screener.py`: 컵앤핸들 알고리즘 탐색 로직 및 가격 데이터 분석 모듈
* `tickers.py`: 한국 거래소(KRX) 종목 및 미국 시장(S&P 500, NASDAQ 100) 티커 정보 추출 모듈
* `requirements.txt`: 프로젝트 의존성 패키지 명세
* `test_sp500_all.py` / `test_sp500_wide.py`: 로컬 테스트 및 대규모 탐색용 스크립트
