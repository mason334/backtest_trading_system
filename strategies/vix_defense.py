from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import ta
import traceback
from playsound import playsound
import math

'''
策略简介
避险：vix超过避险门槛，换成空仓或者低风险资产
抄底：无
relax：如果在持有低风险资产时，vix 降低，解除风险，卖出低风险资产，买入股票。
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

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        if self.defend_status == 0:
            if len(security) == 0:
                if vix > go_safety_vix:
                    if low_risk_symbol != '':
                        stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                        amount = round(self.equity / stock_price) * self.leverage
                        self.enter_stock_order(low_risk_symbol, stock_price, amount)
                        self.defend_status = 1
                else:
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)
            else:
                if vix > go_safety_vix:
                    self.clear_all_stocks()
                    if low_risk_symbol != '':
                        stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                        amount = round(self.equity / stock_price) * self.leverage
                        self.enter_stock_order(low_risk_symbol, stock_price, amount)
                    self.rebalance_flag = 1
                    self.defend_status = 1

        elif self.defend_status == 1:

            #恢复常态
            if vix < relax_vix:
                if len(security) > 0:
                    self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 0

        self.update_position_param()




