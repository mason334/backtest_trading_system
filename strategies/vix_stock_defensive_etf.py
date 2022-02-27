from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
避险：vix超过避险门槛，换成空仓或者低风险资产
抄底：无
relax：如果在持有低风险资产时，vix 降低，解除风险，卖出低风险资产，买入股票。

理由：。

建仓
    选择特定的股票，定好持有股票的数量。
Rebalance
    持续监控VIX水平，如果高于某个水平，就启用低风险股票或者ETF策略,直到VIX降低到某个水平，回到正常持股状态。

'''


class StrategyContext(tp.Context):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']

    def handle_data(self, *args, **kwargs):
        # max_dte = args[0]
        # rebalance_DTE = args[1]
        # open_strike = args[2]
        # rebalance_strike_u = args[3]
        # rebalance_strike_l = args[4]
        activate_low_risk_position_vix = args[0]
        activate_normal_stock_vix = args[1]
        low_risk_symbol = self.underlying_symbol_2

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票还是买option
        if len(security) == 0:
            if vix > activate_low_risk_position_vix:
                stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(low_risk_symbol, stock_price, amount)
            else:
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) > 0:
            if security == self.underlying_symbol:

                if vix > activate_low_risk_position_vix:
                    self.clear_all_stocks()
                    self.rebalance_flag = 1
                    stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(low_risk_symbol, stock_price, amount)
            else:
                if vix > activate_normal_stock_vix:
                    pass
                else:
                    self.clear_all_stocks()
                    self.rebalance_flag = 1
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        self.update_position_param()




