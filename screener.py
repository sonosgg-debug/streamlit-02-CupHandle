import numpy as np
import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr
import yfinance as yf

logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))

def detect_cup_with_handle(df, params=None):
    """
    주가 데이터프레임에서 Cup with Handle 패턴을 탐색합니다.
    
    Parameters:
    - df: columns=['Open', 'High', 'Low', 'Close', 'Volume', 'SMA_200', 'Vol_SMA_20']가 포함된 DataFrame
    - params: 알고리즘 튜닝용 임계값 딕셔너리
    
    Returns:
    - pattern_found: bool
    - details: 패턴 검출 세부 정보 딕셔너리 (검출 실패시 None)
    """
    if df is None or len(df) < 250:
        return False, None

    # 기본 파라미터 설정
    default_params = {
        'min_cup_width': 35,       # 컵 최소 기간 (거래일 기준, 약 7주)
        'max_cup_width': 220,      # 컵 최대 기간 (거래일 기준, 약 10개월)
        'min_cup_depth': 0.10,     # 컵 최소 깊이 (10% 조정)
        'max_cup_depth': 0.50,     # 컵 최대 깊이 (50% 조정)
        'min_handle_width': 5,     # 핸들 최소 기간 (5거래일)
        'max_handle_width': 30,    # 핸들 최대 기간 (30거래일)
        'max_handle_depth': 0.15,  # 핸들 최대 조정 폭 (15% 이내)
        'breakout_vol_factor': 1.5, # 돌파 시 거래량 증가 비율 (20일 평균의 1.5배)
        'prior_trend_gain': 0.25,   # 이전 상승 추세 최소 상승률 (25%)
        'breakout_window': 5,      # 최근 돌파 감지 기간 (최근 N영업일 이내 돌파가 일어남)
    }
    
    if params:
        default_params.update(params)
    p = default_params

    # 계산 편의를 위해 numpy array로 변환
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    volume = df['Volume'].values
    vol_sma20 = df['Vol_SMA_20'].values
    
    n_days = len(df)
    breakout_win = int(p['breakout_window'])
    
    # 컵앤핸들의 돌파 시점(Breakout)은 가장 최근 일봉(오늘) 또는 최근 N일 이내여야 함
    for e_idx in range(n_days - 1, n_days - 1 - breakout_win, -1):
        if e_idx < 100:
            continue
            
        # 돌파일 주가 및 거래량 조건 기본 확인
        current_close = close[e_idx]
        current_vol = volume[e_idx]
        current_vol_sma = vol_sma20[e_idx]
        
        # 돌파 시 거래량 폭증 여부 1차 체크
        if pd.isna(current_vol_sma) or current_vol < current_vol_sma * p['breakout_vol_factor']:
            continue
            
        # 1. 200일선 위에 종가가 있는지 체크 (장기 상승 추세 필터)
        if 'SMA_200' in df.columns:
            sma_200 = df['SMA_200'].values
            if pd.isna(sma_200[e_idx]) or current_close < sma_200[e_idx]:
                continue
                
        # 2. 핸들 시작점(오른쪽 고점, Peak C) 찾기
        # Peak C는 돌파일 e_idx 이전 [e_idx - max_handle_width, e_idx - min_handle_width] 범위에 위치해야 함
        handle_start_min = e_idx - int(p['max_handle_width'])
        handle_start_max = e_idx - int(p['min_handle_width'])
        
        for c_idx in range(handle_start_max, max(0, handle_start_min) - 1, -1):
            c_price = close[c_idx]
            
            # c_idx가 해당 주변(±5일)의 고점인지 확인
            local_window = close[max(0, c_idx - 5): min(n_days, c_idx + 6)]
            if len(local_window) > 0 and c_price < np.max(local_window):
                continue
                
            # 3. 컵의 시작점(왼쪽 고점, Peak A) 찾기
            # Peak A는 Peak C 이전 [c_idx - max_cup_width, c_idx - min_cup_width] 범위에 위치해야 함
            cup_start_min = c_idx - int(p['max_cup_width'])
            cup_start_max = c_idx - int(p['min_cup_width'])
            
            for a_idx in range(cup_start_max, max(0, cup_start_min) - 1, -1):
                a_price = close[a_idx]
                
                # a_idx가 해당 주변(±5일)의 고점인지 확인
                local_window_a = close[max(0, a_idx - 5): min(n_days, a_idx + 6)]
                if len(local_window_a) > 0 and a_price < np.max(local_window_a):
                    continue
                    
                # 컵 왼쪽 고점(A)과 오른쪽 고점(C)의 높이가 대략 비슷한지 검증
                # 보통 오른쪽 고점이 왼쪽 고점 대비 ±15% 내에 있어야 함
                height_ratio = abs(c_price - a_price) / a_price
                if height_ratio > 0.15:
                    continue
                    
                # 4. 컵의 최저점(Valley B) 찾기
                # A_idx와 C_idx 사이에서 가장 낮은 종가 탐색
                cup_range_close = close[a_idx:c_idx + 1]
                if len(cup_range_close) == 0:
                    continue
                b_price = np.min(cup_range_close)
                b_idx = a_idx + np.argmin(cup_range_close)
                
                # 컵 깊이 조건 검증
                cup_depth = (a_price - b_price) / a_price
                if not (p['min_cup_depth'] <= cup_depth <= p['max_cup_depth']):
                    continue
                    
                # 컵 바닥 U자형 둥근 형태 검증
                # 컵 바닥 영역(최저가 b_price에서 컵 깊이의 20% 이내 수준)에 머문 기간이 
                # 전체 컵 기간 (c_idx - a_idx)의 15% 이상인지 체크하여 급격한 V자 반등 필터링
                cup_height = a_price - b_price
                bottom_threshold = b_price + (cup_height * 0.20)
                bottom_days = np.sum(close[a_idx:c_idx + 1] <= bottom_threshold)
                cup_duration = c_idx - a_idx
                if bottom_days / cup_duration < 0.15:
                    continue
                    
                # 5. 핸들의 최저점(Valley D) 찾기
                # C_idx와 돌파 시도일 e_idx 사이에서 가장 낮은 가격 탐색
                handle_range_close = close[c_idx:e_idx]
                if len(handle_range_close) == 0:
                    continue
                d_price = np.min(handle_range_close)
                d_idx = c_idx + np.argmin(handle_range_close)
                
                # 핸들 깊이 조건 검증 (오른쪽 고점 대비 하락률)
                handle_depth = (c_price - d_price) / c_price
                if handle_depth > p['max_handle_depth']:
                    continue
                    
                # 핸들이 컵의 상단 영역에 위치하는지 검증 (컵 바닥과 고점의 중심 위쪽)
                cup_midpoint = (c_price + b_price) / 2.0
                if d_price < cup_midpoint:
                    continue
                    
                # 6. 이전 추세 강도 검증
                # A_idx 이전 100거래일 내 최저가 대비 A_idx의 가격 상승률이 기준 이상인지
                prior_range = close[max(0, a_idx - 100): a_idx]
                if len(prior_range) == 0:
                    continue
                prior_low = np.min(prior_range)
                prior_gain = (a_price - prior_low) / prior_low
                if prior_gain < p['prior_trend_gain']:
                    continue
                    
                # 7. 거래량 메마름 조건 검증
                # 컵 바닥(B_idx 부근) 거래량 확인
                cup_bottom_range_vol = volume[max(a_idx, b_idx - 5): min(c_idx, b_idx + 6)]
                # 컵 시작 전 상승기 거래량 확인
                prior_vol = volume[max(0, a_idx - 20): a_idx]
                if len(cup_bottom_range_vol) > 0 and len(prior_vol) > 0:
                    if np.mean(cup_bottom_range_vol) > np.mean(prior_vol) * 0.70: # 바닥 거래량 감소 확인
                        continue
                        
                # 핸들 구간 거래량 확인
                handle_vol = volume[c_idx:e_idx]
                cup_up_vol = volume[b_idx:c_idx]
                if len(handle_vol) > 0 and len(cup_up_vol) > 0:
                    if np.mean(handle_vol) > np.mean(cup_up_vol) * 0.75: # 핸들 거래량 감소 확인
                        continue
                        
                # 8. 최종 돌파 성공 여부 체크
                # 돌파일 e_idx의 종가가 핸들의 전고점 C_price를 돌파했거나,
                # 핸들 기간 내 최고점 돌파
                handle_max_price = np.max(close[c_idx:e_idx])
                if current_close > handle_max_price:
                    # 모든 조건 충족: 패턴 발견 성공
                    details = {
                        'symbol': df.index.name if df.index.name else 'Unknown',
                        'peak_a_idx': int(a_idx),
                        'peak_a_date': df.index[a_idx].strftime('%Y-%m-%d'),
                        'peak_a_price': float(a_price),
                        'valley_b_idx': int(b_idx),
                        'valley_b_date': df.index[b_idx].strftime('%Y-%m-%d'),
                        'valley_b_price': float(b_price),
                        'peak_c_idx': int(c_idx),
                        'peak_c_date': df.index[c_idx].strftime('%Y-%m-%d'),
                        'peak_c_price': float(c_price),
                        'valley_d_idx': int(d_idx),
                        'valley_d_date': df.index[d_idx].strftime('%Y-%m-%d'),
                        'valley_d_price': float(d_price),
                        'breakout_idx': int(e_idx),
                        'breakout_date': df.index[e_idx].strftime('%Y-%m-%d'),
                        'breakout_price': float(current_close),
                        'cup_depth_pct': float(cup_depth * 100),
                        'handle_depth_pct': float(handle_depth * 100),
                        'cup_width_days': int(cup_duration),
                        'handle_width_days': int(e_idx - c_idx),
                        'volume_increase_ratio': float(current_vol / current_vol_sma)
                    }
                    return True, details
                    
    return False, None

def screen_single_stock(ticker, name, df, params=None):
    """
    개별 주식 데이터프레임을 받아 Cup with Handle 패턴을 분석합니다.
    """
    if df is None or len(df) < 250:
        return None
        
    df_clean = df.dropna(subset=['Close', 'High', 'Low', 'Volume']).copy()
    if len(df_clean) < 250:
        return None
        
    df_clean['SMA_50'] = df_clean['Close'].rolling(window=50).mean()
    df_clean['SMA_150'] = df_clean['Close'].rolling(window=150).mean()
    df_clean['SMA_200'] = df_clean['Close'].rolling(window=200).mean()
    df_clean['Vol_SMA_20'] = df_clean['Volume'].rolling(window=20).mean()
    
    df_clean.index.name = ticker
    
    found, details = detect_cup_with_handle(df_clean, params)
    if found:
        details['name'] = name
        return details
        
    return None


def _process_single_stock(
    ticker: str,
    name: str,
    start_date: str,
    params: dict = None,
    df_cached: pd.DataFrame = None
):
    """
    단일 종목의 데이터를 수집하고 컵앤핸들 패턴을 분석하는 멀티스레딩 통합 워커 함수.
    """
    try:
        if df_cached is not None:
            df = df_cached
        else:
            code = ticker.split('.')[0]
            df = fdr.DataReader(code, start_date)

        if df is None or len(df) < 250:
            return None

        # 미체결 당일 더미 행(Volume=0) 방지 처리
        if len(df) > 1 and df['Volume'].iloc[-1] == 0:
            df = df.iloc[:-1]

        # 거래정지나 최근 5영업일 거래량 전무 종목 제외
        recent_vol = df['Volume'].iloc[-5:].sum()
        if pd.isna(recent_vol) or recent_vol <= 0:
            return None

        df = df.dropna(subset=['Close', 'High', 'Low', 'Volume'])
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if len(df) < 250:
            return None

        return screen_single_stock(ticker, name, df, params)
    except Exception:
        return None


def run_screening_task(
    tickers_df: pd.DataFrame,
    params: dict = None,
    max_workers: int = 24,
    progress_callback = None
) -> pd.DataFrame:
    """
    App-20 초고속 멀티스레딩 엔진 방식을 적용하여
    전체 유니버스 종목의 데이터 수집과 컵앤핸들 기하학 패턴 검증을 완전 병렬로 수행합니다.
    """
    if tickers_df is None or tickers_df.empty:
        return pd.DataFrame()

    total_stocks = len(tickers_df)
    results = []
    completed_count = 0

    # 약 3년 전 날짜부터 수집 (250영업일 이상 이평 및 컵 기간 계산 충족)
    start_date = (datetime.now(KST) - timedelta(days=1095)).strftime('%Y-%m-%d')

    kr_mask = tickers_df['ticker'].str.endswith('.KS') | tickers_df['ticker'].str.endswith('.KQ')
    df_kr = tickers_df[kr_mask].copy()
    df_us = tickers_df[~kr_mask].copy()

    # 1. 한국 주식: FinanceDataReader 기반 초고속 멀티스레딩 원스톱 수집 & 분석
    if not df_kr.empty:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {
                executor.submit(
                    _process_single_stock,
                    row['ticker'],
                    row['회사명'],
                    start_date,
                    params
                ): (row['ticker'], row['회사명'])
                for _, row in df_kr.iterrows()
            }

            for future in as_completed(future_to_stock):
                ticker, name = future_to_stock[future]
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, total_stocks, name)
                try:
                    res = future.result()
                    if res is not None:
                        results.append(res)
                except Exception:
                    pass

    # 2. 미국 주식: yfinance 일괄 다운로드 후 멀티스레드 병렬 분석
    if not df_us.empty:
        us_tickers = df_us['ticker'].tolist()
        name_map = dict(zip(df_us['ticker'], df_us['회사명']))
        try:
            data = yf.download(us_tickers, period="3y", group_by="ticker", progress=False, timeout=20)
            us_stock_dfs = {}
            for t in us_tickers:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        ticker_level = 'Ticker' if 'Ticker' in data.columns.names else 1
                        tickers_in_data = data.columns.get_level_values(ticker_level).unique()
                        if t not in tickers_in_data:
                            continue
                        df_single = data.xs(t, level=ticker_level, axis=1).dropna(subset=['Close', 'High', 'Low', 'Volume'])
                    else:
                        df_single = data.dropna(subset=['Close', 'High', 'Low', 'Volume'])

                    if df_single.index.tz is not None:
                        df_single.index = df_single.index.tz_localize(None)

                    if len(df_single) >= 250:
                        us_stock_dfs[t] = df_single
                except Exception:
                    continue

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_us = {
                    executor.submit(
                        _process_single_stock,
                        t,
                        name_map[t],
                        start_date,
                        params,
                        us_stock_dfs[t]
                    ): (t, name_map[t])
                    for t in us_stock_dfs
                }

                for future in as_completed(future_to_us):
                    t, name = future_to_us[future]
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_stocks, name)
                    try:
                        res = future.result()
                        if res is not None:
                            results.append(res)
                    except Exception:
                        pass
        except Exception as e:
            print(f"미국 주식 다운로드 중 오류: {e}")

    if not results:
        return pd.DataFrame()

    df_res = pd.DataFrame(results)
    # 거래량 비율 기준 내림차순 정렬
    if 'volume_increase_ratio' in df_res.columns:
        df_res = df_res.sort_values(by='volume_increase_ratio', ascending=False).reset_index(drop=True)

    return df_res
