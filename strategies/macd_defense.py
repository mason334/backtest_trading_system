from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import ta
import traceback
from playsound import playsound
import math

'''
策略简介
本策略下，账户可能存在两种状态：defend status = 0 or 1.
不会存在buy dip status.

                    buy dip status
                       0    1
                |---|----|----|    
defend status   |0  | ↓  |    |   
                |---|---------|                
                |1  | ↑  |    | 
                |---|----|----|

第一个数字代表defend status, 第二个数字代表buy dip status，箭头代表状态改变的方向。
    0, 0 ↓: MACD出现死叉，换成空仓或者低风险资产(出现金叉时，不动).
    1, 0 ↑: vix < relax_vix, 清仓低风险资产，买入基础资产。
2020/8/16 zxc update

'''


class StrategyContext(tp.Context):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']

    def handle_data(self, *args, **kwargs):
        go_safety_vix = args[0]
        relax_vix = args[1]
        # buy_dip_vix = args[2]
        low_risk_symbol = self.underlying_symbol_2

        # 读取当前日期macd_histogram的值，备后面判断交易条件
        macd_histogram = self.stock_with_macd.loc[self.current_dt, 'MACD_Histogram']

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        if self.defend_status == 0:
            if macd_histogram > 0:
                if len(security) == 0:
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                elif len(security) != 0:
                    pass

            if macd_histogram < 0:
                self.clear_all_stocks()
                if low_risk_symbol != '':
                    stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(low_risk_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 1

        elif self.defend_status == 1:
            # 恢复常态
            if vix < relax_vix:
                if len(security) > 0:
                    self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 0

        self.update_position_param()




