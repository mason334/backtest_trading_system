from backtest_trading_system import trading_tools as tools
import ta
import pandas as pd

df = pd.DataFrame()
stock_data = tools.get_full_data_from_sql_tock('goog')
print(stock_data.head())
# df['bb_high_indicator'] = ta.volatility.bollinger_hband_indicator(stock_data["Adj Close"], n=20, ndev=2, fillna=True)
# print(df)

macd = ta.trend.MACD(stock_data["Adj Close"])
stock_data["MACD"] = macd.macd()
stock_data["MACD_Signal"] = macd.macd_signal()
stock_data["MACD_Histogram"] = macd.macd_diff()

ema1 = stock_data["Adj Close"].ewm(span=12, min_periods=12, adjust=False).mean()
ema1true = stock_data["Adj Close"].ewm(span=12, min_periods=12, adjust=True).mean()
ema2 = stock_data["Adj Close"].ewm(span=12, adjust=False).mean()
stock_data.to_csv('E:\\Strategy_output\\MACD\\goog.csv')