from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
买入股票不动，主要用于一些参数的计算
'''


class StrategyContext(tp.Context):
    def handle_data(self, *args, **kwargs):

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空，买股票
        if len(security) == 0:
            stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
            amount = round(self.equity / stock_price) * self.leverage
            self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        self.update_position_param()




