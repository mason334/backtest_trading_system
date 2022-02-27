from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import ta
import traceback
from playsound import playsound
import math

'''
策略简介
避险：vix超过避险门槛，换成空仓或者低风险资产
抄底：defend status下，vix高于一定水平（可以设定很低，让这个参数失效），MACD出现金叉
relax：如果在持有低风险资产时，vix 降低，解除风险，卖出低风险资产，买入股票。
'''


class StrategyContext(tp.Context):
    # def __init__(self):
    #     super().__init__()
        # self.stock_with_macd = pd.DataFrame()

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']

    def handle_data(self, *args, **kwargs):
        go_safety_vix = args[0]
        relax_vix = args[1]
        buy_dip_vix = args[2]

        low_risk_symbol = self.underlying_symbol_2

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        # 读取当前日期macd_histogram的值，备后面判断交易条件
        macd_histogram = self.stock_with_macd.loc[self.current_dt, 'MACD_Histogram']

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票
        # if (self.defend_status == 0) and (len(security) == 0):
        #     if (vix > go_safety_vix) and (vix < buy_dip_vix):
        #         if low_risk_symbol != '':
        #             stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
        #             amount = round(self.equity / stock_price) * self.leverage
        #             self.enter_stock_order(low_risk_symbol, stock_price, amount)
        #
        #             self.defend_status = 1
        #             # self.opt_substitution_flag = 1
        #     else:
        #         stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
        #         amount = round(self.equity / stock_price) * self.leverage
        #         self.enter_stock_order(self.underlying_symbol, stock_price, amount)
        #
        # # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉风险仓位，进行防守
        # elif self.defend_status == 0 and security == self.underlying_symbol:
        #     if self.buy_dip_status == 1:
        #         if vix < relax_vix:
        #             self.buy_dip_status = 0
        #     else:
        #         if vix > go_safety_vix:
        #             self.clear_all_stocks()
        #             if low_risk_symbol != '':
        #                 stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
        #                 amount = round(self.equity / stock_price) * self.leverage
        #                 self.enter_stock_order(low_risk_symbol, stock_price, amount)
        #
        #             self.rebalance_flag = 1
        #             self.defend_status = 1
        #             # self.opt_substitution_flag = 1

        if self.defend_status == 0:
            if self.buy_dip_status == 1:
                if vix < relax_vix:
                    self.buy_dip_status = 0
            else:
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

            # 恢复常态
            if vix < relax_vix:
                if len(security) > 0:
                    self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 0

            # 抄底
            elif (vix > buy_dip_vix) and (macd_histogram > 0):
                if len(security) > 0:
                    self.clear_all_stocks()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.buy_dip_status = 1
                self.defend_status = 0

        self.update_position_param()




