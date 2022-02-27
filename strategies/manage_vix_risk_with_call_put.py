from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math
'''

策略简介
动态股票期权替换策略，交易期间根据VIX水平，调整仓位是option还是股票。
股票持仓的时候，可以在交易参数中设定，是否使用杠杆。

理由：期权主要功能体现在抗跌上，如果不出现大跌，option策略在不加杠杆的情况下很难跑赢大盘或者underlying。

建仓
    选择特定的股票，定好持有股票的数量。
Rebalance
    持续监控VIX水平，如果高于某个水平，就启用long call 策略,知道VIX降低到某个水平，或者股价降低到某个水平。
    然后清空call仓位，回到持股状态。
long call 策略
    选择特定的档期、strike的call，
    call数量：根据全仓持股的数量，计算出应该买入的call数量
    call rebalance：3个主要条件，
        1 特定的DTE到达
        2 股价上升到一定幅度
        3 股价下降到一定幅度
'''


class StrategyContext(tp.OptionContext):

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.previous_vix = 0
        self.option_maintenance_margin = 0.1

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        activate_option_vix = args[3]
        activate_stock_vix = args[4]
        ma_n = args[5]

        self.update_position_param()

        vix = tp.quote_vix_open(self.current_dt)
        vix_ma = tp.moving_average('vix', ma_n, self.current_dt)
        # vix_ma = vix

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票还是买option
        if len(security) == 0:
            if vix > activate_option_vix:
                self.construct_put(max_dte, open_strike, delta_factor=-1, stock_sub=False)
                # self.previous_vix = tp.quote_vix_high(self.current_dt)
            else:
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) < 5:
            if vix > activate_option_vix:
                self.clear_all_stocks()
                self.construct_put(max_dte, open_strike, delta_factor=-1, stock_sub=False)
        # 检查仓位结果为Option仓位。检查VIX后，决定继续持有option并坚持rebalance，还是清掉option换成股票
        elif len(security) > 5:
            if vix < activate_stock_vix:
                self.clear_all_options()
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

            else:
                # check 是call还是put
                if self.positions.loc[security, 'Type'] == 'call':
                    if vix > self.previous_vix:
                        self.clear_all_options()
                        self.construct_put(max_dte, open_strike, delta_factor=-1, stock_sub=False)
                        self.rebalance_flag = 1
                    else:
                        condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
                        condition_4 = False  # contract 第二天是否消失
                        # 检查第二天是否有contract
                        today_index = self.date_range.index(self.current_dt)
                        next_day_index = today_index + 1
                        next_day = self.date_range[next_day_index]
                        try:
                            tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
                        except Exception as error:
                            if f'{error}' == 'contract_error':
                                condition_4 = True
                        if condition_1 or condition_4:
                            print(f'rebalanced')
                            print(f'condition_1, condition_4')
                            print(f'{condition_1}, {condition_4}')
                            self.rebalance_flag = 1
                            # 先清掉option仓位
                            self.clear_all_options()
                            # 再重新建立合适的仓位
                            self.construct_call(max_dte, open_strike, stock_sub=False, delta_factor=-1)

                elif self.positions.loc[security, 'Type'] == 'put':
                    if vix > self.previous_vix:
                        condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
                        condition_4 = False  # contract 第二天是否消失
                        # 检查第二天是否有contract
                        today_index = self.date_range.index(self.current_dt)
                        next_day_index = today_index + 1
                        next_day = self.date_range[next_day_index]
                        try:
                            tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
                        except Exception as error:
                            if f'{error}' == 'contract_error':
                                condition_4 = True

                        if condition_1 or condition_4:
                            print(f'rebalanced')
                            print(f'condition_1, condition_4')
                            print(f'{condition_1}, {condition_4}')
                            self.rebalance_flag = 1
                            # 先清掉option仓位
                            self.clear_all_options()
                            # 再重新建立合适的仓位
                            self.construct_put(max_dte, open_strike, delta_factor=-1, stock_sub=False)

                    else:
                        self.clear_all_options()
                        self.construct_call(max_dte, open_strike, stock_sub=False, delta_factor=-1)
                        self.rebalance_flag = 1

        self.previous_vix = vix_ma
        self.update_position_param()
