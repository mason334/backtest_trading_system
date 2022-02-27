from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import ta
import traceback
from playsound import playsound
import math

'''
基于MACD信号的策略
出现金叉全仓买入。
出现死叉卖出清仓，不持有仓位。
2020/8/16 zxc update
'''


class StrategyContext(tp.Context):
    def __init__(self):
        super().__init__()
        self.stock_with_macd = pd.DataFrame()

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.stock_with_macd = tp.get_full_data_from_sql_tock(self.underlying_symbol)
        _macd = ta.trend.MACD(self.stock_with_macd["Adj Close"])
        self.stock_with_macd["MACD"] = _macd.macd()
        self.stock_with_macd["MACD_Signal"] = _macd.macd_signal()
        self.stock_with_macd["MACD_Histogram"] = _macd.macd_diff()
        self.stock_with_macd.set_index('Date', drop=True, inplace=True)

    def handle_data(self, *args, **kwargs):
        # rebalance_DTE = args[1]
        # open_strike = args[2]
        # rebalance_strike_u = args[3]
        # rebalance_strike_l = args[4]
        # go_safety_vix = args[0]
        # relax_vix = args[1]
        # buy_dip_vix = args[2]
        # low_risk_symbol = self.underlying_symbol_2

        self.update_position_param()

        # 读取当前日期macd_histogram的值，备后面判断交易条件
        macd_histogram = self.stock_with_macd.loc[self.current_dt, 'MACD_Histogram']

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查MACD_HISTOGRAM后，决定是否买入股票（全仓买入）
        if len(security) == 0:
            if macd_histogram > 0:
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1

        # 检查仓位结果为股票仓位。检查MACD_HISTOGRAM后，决定是否清仓
        else:
            if macd_histogram < 0:
                self.clear_all_stocks()
                self.rebalance_flag = 1

        self.update_position_param()
