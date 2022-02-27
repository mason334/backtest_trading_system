from backtest_trading_system import trading_platform_stock_only as tp
import ta
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
可能出现的status组合
                    buy dip status
                       0    1
                |---|----|----|    
defend status   |0  | ↓  |  ← |   
                |---|---------|                
                |1  | ↑ ↗|    | 
                |---|----|----|
先判断account status，只有三种status。
在某种status下，再判断vix情况，如果满足相应的情况，就要进行status的迁移。
迁移方式只有图中箭头的迁移方式。



第一个数字代表defend status, 第二个数字代表buy dip status，箭头代表状态改变的方向。
正常安全状态（0，0）下，根据MACD，动态循环调仓。
    如果今天MACD<0,并且在MACD第二天会金叉时（需要窥见未来的能力），买入基础风险资产。
    同时记录持仓时间，如果持仓风险资产时间达到holding_period，清仓。
    再次进入上面的循环
0, 0 ↓: (vix > go_safety_vix) and (vix < buy_dip_vix), 买入低风险资产
1, 0 ↑: vix < relax_vix，清理低风险仓位。
1, 0 ↗: vix > buy_dip_vix, 清理低风险仓位，再全仓买入基础资产。
0, 1 ←: vix < relax_vix, 清理所有long、short仓位，再全仓买入基础资产。

Updated 2020/9/19
'''


class StrategyContext(tp.Context):
    def __init__(self):
        super().__init__()
        self.buy_dip_status = 0
        self.defend_status = 0
        self.holding_period_counter = 0 # 定义一个holding period,用于记录持有股票的时间。

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']

        self.stock_with_macd = tp.get_full_data_from_sql_tock(self.underlying_symbol)
        _macd = ta.trend.MACD(self.stock_with_macd["Adj Close"])
        self.stock_with_macd["MACD"] = _macd.macd()
        self.stock_with_macd["MACD_Signal"] = _macd.macd_signal()
        self.stock_with_macd["MACD_Histogram"] = _macd.macd_diff()
        self.stock_with_macd.set_index('Date', drop=True, inplace=True)

    def handle_data(self, *args, **kwargs):
        go_safety_vix = args[0]
        relax_vix = args[1]
        buy_dip_vix = args[2]
        holding_period = args[3]
        low_risk_symbol = self.underlying_symbol_2

        self.update_position_param()

        # 读取当前日期macd_histogram的值，备后面判断交易条件
        macd_histogram = self.stock_with_macd.loc[self.current_dt, 'MACD_Histogram']
        macd = self.stock_with_macd.loc[self.current_dt, 'MACD']
        vix = tp.quote_vix_high(self.current_dt)

        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        next_day = self.date_range[next_day_index]
        next_day_macd_histogram = self.stock_with_macd.loc[next_day, 'MACD_Histogram']

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉风险仓位，进行防守
        if self.defend_status == 0:
            if self.buy_dip_status == 0:
                if vix < go_safety_vix:
                    # vix较低的水平，空仓的情况，第二天会金叉的时候，今天买入股票（相当于看到了未来）
                    if len(security) == 0:
                        if (macd_histogram < 0) and (next_day_macd_histogram > 0):
                            stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                            amount = round(self.equity / stock_price) * self.leverage
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.rebalance_flag = 1
                    elif len(security) > 0:
                        self.holding_period_counter += 1
                        if self.holding_period_counter == holding_period:
                            self.clear_all_stocks()
                            self.holding_period_counter = 0
                            self.rebalance_flag = 1

                elif (vix > go_safety_vix) and (vix < buy_dip_vix):
                    self.clear_all_stocks()
                    self.update_position_param()
                    if low_risk_symbol != '':
                        # 买入low risk asset
                        stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                        amount = round(self.equity / stock_price) * self.leverage
                        self.enter_stock_order(low_risk_symbol, stock_price, amount)

                    self.rebalance_flag = 1
                    self.defend_status = 1
                    self.holding_period_counter = 0

                elif vix > buy_dip_vix:
                    pass

            elif self.buy_dip_status == 1:
                if vix < relax_vix:
                    self.buy_dip_status = 0

        elif self.defend_status == 1:
            if vix < relax_vix:
                self.clear_all_stocks()
                self.update_position_param()
                # stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                # amount = round(self.equity / stock_price) * self.leverage
                # self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 1
                self.defend_status = 0
                self.holding_period_counter = 0


            elif vix > buy_dip_vix:
                self.clear_all_stocks()
                self.update_position_param()
                stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

                self.rebalance_flag = 1
                self.buy_dip_status = 1
                self.defend_status = 0
                self.holding_period_counter = 0

        self.update_position_param()


    # def handle_data_1(self, *args, **kwargs):
    #     # max_dte = args[0]
    #     # rebalance_DTE = args[1]
    #     # open_strike = args[2]
    #     # rebalance_strike_u = args[3]
    #     # rebalance_strike_l = args[4]
    #     go_safety_vix = args[0]
    #     relax_vix = args[1]
    #     buy_dip_vix = args[2]
    #     low_risk_symbol = self.underlying_symbol_2
    #
    #     self.update_position_param()
    #
    #     vix = tp.quote_vix_high(self.current_dt)
    #
    #     if len(self.positions.SecuritySymbol.values) == 0:
    #         security = ''
    #     else:
    #         security = self.positions.SecuritySymbol.values[0]
    #
    #     # 检查position为空。后续检查VIX后，决定买股票还是买option
    #     if (self.defend_status == 0) and (len(security) == 0):  # 账户状态检查
    #         if (vix > go_safety_vix) and (vix < buy_dip_vix):  # 账户状态转换条件检查
    #             if low_risk_symbol != '':
    #                 stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
    #                 amount = round(self.equity / stock_price) * self.leverage
    #                 self.enter_stock_order(low_risk_symbol, stock_price, amount)
    #
    #                 self.defend_status = 1
    #                 self.opt_substitution_flag = 1
    #         else:
    #             stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
    #             amount = round(self.equity / stock_price) * self.leverage
    #             self.enter_stock_order(self.underlying_symbol, stock_price, amount)
    #
    #     # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉风险仓位，进行防守
    #     elif self.defend_status == 0 and security == self.underlying_symbol:
    #         if self.buy_dip_status == 1:
    #             if vix < relax_vix:
    #                 self.buy_dip_status = 0
    #         else:
    #             if vix > go_safety_vix:
    #                 self.clear_all_stocks()
    #                 if low_risk_symbol != '':
    #                     stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
    #                     amount = round(self.equity / stock_price) * self.leverage
    #                     self.enter_stock_order(low_risk_symbol, stock_price, amount)
    #
    #                 self.rebalance_flag = 1
    #                 self.defend_status = 1
    #                 self.opt_substitution_flag = 1
    #
    #     elif self.defend_status == 1:
    #         if vix < relax_vix:
    #             self.clear_all_stocks()
    #             stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
    #             amount = round(self.equity / stock_price) * self.leverage
    #             self.enter_stock_order(self.underlying_symbol, stock_price, amount)
    #
    #             self.rebalance_flag = 1
    #             self.defend_status = 0
    #             self.opt_substitution_flag = 0
    #
    #         elif vix > buy_dip_vix:
    #             self.clear_all_stocks()
    #             stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
    #             amount = round(self.equity / stock_price) * self.leverage
    #             self.enter_stock_order(self.underlying_symbol, stock_price, amount)
    #
    #             self.rebalance_flag = 1
    #             self.buy_dip_status = 1
    #             self.defend_status = 0
    #             self.opt_substitution_flag = 0
    #
    #
    #     self.update_position_param()