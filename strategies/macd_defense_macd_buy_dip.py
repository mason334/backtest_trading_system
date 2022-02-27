from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import ta
import traceback
from playsound import playsound
import math

'''
策略简介
                    buy dip status
                       0    1
                |---|----|----|    
defend status   |0  | ↓  |  ← |   
                |---|---------|                
                |1  |↑ ↗ |    | 
                |---|----|----|

第一个数字代表defend status, 第二个数字代表buy dip status，箭头代表状态改变的方向。
    0, 0 ↓: MACD出现死叉，进入防御状态。换成空仓或者低风险资产。
    1, 0 ↑: vix < relax_vix, 清仓低风险资产，买入基础资产。relax。
    1, 0 ↗: 根据金叉和vix抄底，(vix > buy_dip_vix) and (macd_histogram > 0), 清仓低风险资产，买入基础资产。
    0, 1 ←: vix < relax_vix，更新account status为 无风险状态。不操作仓位。relax。
    
2020/8/16 zxc update

'''


class StrategyContext(tp.Context):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']


    def handle_data(self, *args, **kwargs):
        go_safety_vix = args[0]
        relax_vix = args[1]
        buy_dip_vix = args[2]
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
            if self.buy_dip_status == 0:
                if macd_histogram > 0:
                    if len(security) == 0:
                        stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                        amount = round(self.equity / stock_price) * self.leverage
                        self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                    elif len(security) > 0:
                        pass
                elif macd_histogram < 0:
                    self.clear_all_stocks()
                    if low_risk_symbol != '':
                        stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                        amount = round(self.equity / stock_price) * self.leverage
                        self.enter_stock_order(low_risk_symbol, stock_price, amount)
                    self.defend_status = 1
                    self.rebalance_flag = 1
            elif self.buy_dip_status == 1:
                if vix < relax_vix:
                    self.buy_dip_status = 0
        elif self.defend_status == 1:
            # 恢复常态
            if vix < relax_vix:
                self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 0

            # 抄底
            elif (vix > buy_dip_vix) and (macd_histogram > 0):
                self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.buy_dip_status = 1
                self.defend_status = 0

        self.update_position_param()




