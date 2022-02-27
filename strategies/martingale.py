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

martingale 策略，是越跌越买。本策略一共分了6个价格水平来买入。
建仓时的价格作为参考价格。如果价格上涨，参考价格随之调整为最新价格。
价格如果下跌，进入5%，10%，15%，20%，25%，30%构成的网格中，需要调仓。
根据下跌不同的百分比，买入不同level的仓位。这些仓位level可以设定，但是必须是递增的。
  一种特殊情况，如果仓位设定是固定仓位并且大于1（有杠杆），随着价格上升，杠杆率会下降。所以在回撤的时候算法会比较仓位，导致加仓。
  这里价格下跌不会导致调仓，因为价格下跌会导致杠杆率升高。
  如果设定仓位是固定仓位并且小于1，价格上涨不会导致调仓。但是价格下降，有可能导致仓位低于原始仓位，在回撤中可能导致调仓。价格新高时也会导致调仓。
所以每个级别有判断仓位的条件，仓位比价格级别要求仓位的小了，就要加仓到目标仓位。
价格反弹过程中，不减仓。
如果价格反弹涨回reference price，减仓到level 1.

2021/06/12 zxc update

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
        if self.defend_status == 0:
            if self.buy_dip_status == 0:
                if (vix < go_safety_vix) and (len(security) == 0):
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    amount = round(self.equity / stock_price * level_1)
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                    self.reference_price = stock_price
                    # self.martingale_equity = self.equity

                elif (vix < go_safety_vix) and (len(security) != 0):
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
                    if (stock_price - self.reference_price)/self.reference_price < -0.05:

                        if (-0.1 < (stock_price - self.reference_price)/self.reference_price < -0.05) and (self.positions_value < self.equity *
                                                                                                           level_2):
                            amount = round((self.equity * level_2 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.15 < (stock_price - self.reference_price)/self.reference_price < -0.1) and (self.positions_value < self.equity *
                                                                                                             level_3):
                            amount = round((self.equity * level_3 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.2 < (stock_price - self.reference_price)/self.reference_price < -0.15) and (self.positions_value < self.equity *
                                                                                                             level_4):
                            amount = round((self.equity * level_4 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif (-0.3 < (stock_price - self.reference_price)/self.reference_price < -0.20) and (self.positions_value < self.equity *
                                                                                                             level_5):
                            amount = round((self.equity * level_5 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        elif ((stock_price - self.reference_price)/self.reference_price < -0.30) and (self.positions_value < self.equity *
                                                                                                             level_6):
                            amount = round((self.equity * level_6 - self.positions_value)/stock_price)
                            self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                            self.martingale_status = 1
                            self.rebalance_flag = 1
                        # print(self.current_dt)
                        # print(f'reference price is {self.reference_price}')
                        # print(f'today equity is {self.equity} and leverage is {self.loan / self.equity}')
                        # print(f"price level is {round((stock_price - self.reference_price)/self.reference_price, 2)}")
                    elif ((stock_price - self.reference_price)/self.reference_price >= 0) and (self.martingale_status == 1):
                        self.clear_all_stocks()
                        amount = round(self.equity / stock_price * level_1)
                        self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                        self.reference_price = stock_price
                        self.martingale_status = 0
                        self.rebalance_flag = 1
                        # print(self.current_dt)
                        # print("position returned to level 1 and out of martingale status!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    elif ((stock_price - self.reference_price)/self.reference_price >= 0) and (self.martingale_status == 0):
                        self.reference_price = stock_price

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
                    self.rebalance_flag = 1
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
                self.rebalance_flag = 1
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
        # print(f'reference price is {self.reference_price}')
        self.update_position_param()




