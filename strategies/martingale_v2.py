from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
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

martingale 策略，是越跌越买。

根据下跌不同的百分比，买入不同level的仓位。
本策略一共分了6个level来买入。
这个v2版本的，是越跌，仓位越低。
所以每个级别有判断仓位的条件，仓位比价格级别要求仓位的大了，就要减仓到目标仓位。仓位参数必须是递减的。
但是价格不涨回原参考价，仓位不调整上升。直到涨回原价，才一步到位调整回来。
但是，如果仓位比目标仓位的低，除非回到reference price, 否则是不调整仓位的。

2021/07/24 zxc update

'''


class StrategyContext(tp.Context):
    def __init__(self):
        super().__init__()
        self.buy_dip_status = 0
        self.defend_status = 0
        self.martingale_status = 0

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.underlying_symbol_2 = kwargs['underlying_symbol_2']

    def handle_data(self, *args, **kwargs):
        # max_dte = args[0]
        # rebalance_DTE = args[1]
        # open_strike = args[2]
        # rebalance_strike_u = args[3]
        # rebalance_strike_l = args[4]
        go_safety_vix = args[0]
        relax_vix = args[1]
        buy_dip_vix = args[2]
        level_1 = args[3]
        level_2 = args[4]
        level_3 = args[5]
        level_4 = args[6]
        level_5 = args[7]
        level_6 = args[8]

        low_risk_symbol = self.underlying_symbol_2

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        ## 检查position为空。后续检查VIX后，决定买股票还是买option
        # if (self.defend_status == 0) and (len(security) == 0):  # 账户状态检查
        #     if (vix > go_safety_vix) and (vix < buy_dip_vix):  # 账户状态转换条件检查
        #         if low_risk_symbol != '':
        #             stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
        #             amount = round(self.equity / stock_price) * self.leverage
        #             self.enter_stock_order(low_risk_symbol, stock_price, amount)
        #
        #             self.defend_status = 1
        #             self.opt_substitution_flag = 1
        #     else:
        #         stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
        #         amount = round(self.equity / stock_price) * self.leverage
        #         self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉风险仓位，进行防守
        # print(self.current_dt)
        if self.defend_status == 0:
            if self.buy_dip_status == 0:
                if (vix < go_safety_vix) and (len(security) == 0) and (self.martingale_status == 0):
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    amount = round(self.equity / stock_price * level_1)
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                    self.reference_price = stock_price
                    # self.martingale_equity = self.equity

                elif (vix < go_safety_vix) and (len(security) != 0):
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    if (stock_price - self.reference_price)/self.reference_price < -0.05:

                        if (-0.1 < (stock_price - self.reference_price)/self.reference_price < -0.05) and (self.positions_value > self.equity *
                                                                                                           level_2):
                            amount = round((self.equity * level_2 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.15 < (stock_price - self.reference_price)/self.reference_price < -0.1) and (self.positions_value > self.equity *
                                                                                                             level_3):
                            amount = round((self.equity * level_3 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.2 < (stock_price - self.reference_price)/self.reference_price < -0.15) and (self.positions_value > self.equity *
                                                                                                             level_4):
                            amount = round((self.equity * level_4 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.3 < (stock_price - self.reference_price)/self.reference_price < -0.20) and (self.positions_value > self.equity *
                                                                                                             level_5):
                            amount = round((self.equity * level_5 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif ((stock_price - self.reference_price)/self.reference_price < -0.30) and (self.positions_value > self.equity *
                                                                                                             level_6):
                            amount = round((self.equity * level_6 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        # print(f'today equity is {self.equity} and leverage is {self.positions_value / self.equity}')
                        # print(f"price level is {round((stock_price - self.reference_price)/self.reference_price, 4)}")
                        # print(f'rebalanced')
                    elif ((stock_price - self.reference_price)/self.reference_price >= 0) and (self.martingale_status == 1):
                        self.clear_all_stocks()
                        amount = round(self.equity / stock_price * level_1)
                        self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                        self.reference_price = stock_price
                        self.martingale_status = 0
                        self.rebalance_flag = 1
                        # print("position returned and out of martingale status!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    elif ((stock_price - self.reference_price)/self.reference_price >= 0) and (self.martingale_status == 0):
                        self.reference_price = stock_price
                        # print('prince go higher, adjusted price up')

                elif (vix > go_safety_vix) and (vix < buy_dip_vix):
                    self.clear_all_stocks()
                    # if low_risk_symbol != '':
                    #     # 做多underlying
                    #     stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    #
                    #
                    #     amount = round(self.equity / stock_price) * self.leverage
                    #     self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                    #     # 做空hedging position
                    #     stock_price = tp.quote_stock(low_risk_symbol, self.current_dt)
                    #     amount = -round(self.equity / stock_price) * self.leverage
                    #     self.enter_stock_order(low_risk_symbol, stock_price, amount)
                    #
                    # self.rebalance_flag = 1
                    self.defend_status = 1
                    pass
                elif vix > buy_dip_vix:
                    pass

            elif self.buy_dip_status == 1:
                if vix < relax_vix:
                    self.buy_dip_status = 0

        elif self.defend_status == 1:
            if vix < relax_vix:
                self.clear_all_stocks()
                # self.rebalance_flag = 1
                self.defend_status = 0
            #
            # elif vix > buy_dip_vix:
            #     self.clear_all_stocks()
            #     stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
            #     amount = round(self.equity / stock_price) * self.leverage
            #     self.enter_stock_order(self.underlying_symbol, stock_price, amount)
            #
            #     self.rebalance_flag = 1
            #     self.buy_dip_status = 1
            #     self.defend_status = 0
        # print(self.reference_price)
        self.update_position_param()




