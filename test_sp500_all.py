import pandas as pd
import yfinance as yf
from tickers import get_krx_tickers
from screener import screen_single_stock

def test_sp500():
    df_sp = get_krx_tickers('S&P 500')
    tickers_list = df_sp['ticker'].tolist()
    name_map = dict(zip(df_sp['ticker'], df_sp['회사명']))
    
    print(f"Total S&P 500 tickers: {len(tickers_list)}")
    
    # Download in chunks of 50
    chunk_size = 50
    chunks = [tickers_list[i:i + chunk_size] for i in range(0, len(tickers_list), chunk_size)]
    
    detected = []
    
    for idx, chunk in enumerate(chunks):
        print(f"Processing chunk {idx+1}/{len(chunks)}...")
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
                        
                    res = screen_single_stock(ticker, name_map[ticker], df_single)
                    if res:
                        detected.append(res)
                        print(f"★ DETECTED: {ticker} ({name_map[ticker]}) -> Breakout: {res['breakout_date']}, Vol: {res['volume_increase_ratio']:.2f}")
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Chunk {idx+1} download failed: {e}")
            
    print(f"\nDone! Detected {len(detected)} stocks in S&P 500.")
    if len(detected) > 0:
        print(pd.DataFrame(detected)[['symbol', 'name', 'breakout_date', 'breakout_price', 'cup_depth_pct', 'handle_depth_pct']])

if __name__ == "__main__":
    test_sp500()
