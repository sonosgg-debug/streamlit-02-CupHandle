import pandas as pd
import yfinance as yf
from tickers import get_krx_tickers
from screener import screen_single_stock

def test_sp500_wide():
    df_sp = get_krx_tickers('S&P 500')
    tickers_list = df_sp['ticker'].tolist()
    name_map = dict(zip(df_sp['ticker'], df_sp['회사명']))
    
    print(f"Total S&P 500 tickers: {len(tickers_list)}")
    
    # Use 30 days breakout window, other parameters are standard
    params = {
        'min_cup_width': 35,
        'max_cup_width': 220,
        'min_cup_depth': 0.10,
        'max_cup_depth': 0.50,
        'min_handle_width': 5,
        'max_handle_width': 30,
        'max_handle_depth': 0.15,
        'breakout_vol_factor': 1.5,
        'prior_trend_gain': 0.25,
        'breakout_window': 30  # Look back 30 trading days
    }
    
    # Download first 100 tickers for a faster test
    test_tickers = tickers_list[:150]
    print(f"Testing a subset of {len(test_tickers)} S&P 500 tickers with 30-day breakout window...")
    
    chunk_size = 50
    chunks = [test_tickers[i:i + chunk_size] for i in range(0, len(test_tickers), chunk_size)]
    
    detected = []
    for idx, chunk in enumerate(chunks):
        try:
            data = yf.download(chunk, period="3y", group_by="ticker", progress=False)
            for ticker in chunk:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        ticker_level = 'Ticker' if 'Ticker' in data.columns.names else 1
                        df_single = data.xs(ticker, level=ticker_level, axis=1).dropna(subset=['Close', 'High', 'Low', 'Volume'])
                    else:
                        df_single = data.dropna(subset=['Close', 'High', 'Low', 'Volume'])
                        
                    if len(df_single) < 250:
                        continue
                        
                    res = screen_single_stock(ticker, name_map[ticker], df_single, params)
                    if res:
                        detected.append(res)
                        print(f"★ DETECTED (Wide Window): {ticker} ({name_map[ticker]}) -> Breakout: {res['breakout_date']}, Vol Ratio: {res['volume_increase_ratio']:.2f}")
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Chunk download failed: {e}")
            
    print(f"\nDone! Detected {len(detected)} stocks in the S&P 500 subset with 30-day breakout window.")

if __name__ == "__main__":
    test_sp500_wide()
