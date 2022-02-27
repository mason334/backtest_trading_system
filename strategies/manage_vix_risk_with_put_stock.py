from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''

策略简介
动态股票期权替换策略，交易期间根据VIX水平，调整仓位是option还是股票。
股票持仓的时候，可以在交易参数中设定，是否使用杠杆。

理由：用vix来识别趋势。下跌的时候，买入put。

建仓
    选择特定的股票，定好持有股票的数量。
Rebalance
    持续监控VIX水平，如果vix上升且高于触发值，就买入put。
    其他情况持有股票
long put 策略

    put rebalance：3个主要条件，
        1 特定的DTE到达
        2 股价上升到一定幅度
        3 股价下降到一定幅度
'''


class StrategyContext(tp.OptionContext):

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.previous_vix = 0

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        rebalance_strike_u = args[3]
        rebalance_strike_l = args[4]
        activate_option_vix = args[5]
        activate_stock_vix = args[6]

        self.update_position_param()

        vix = tp.quote_vix_open(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票还是买option
        if len(security) == 0:
            if vix > activate_option_vix:
                self.construct_put(max_dte, open_strike, delta_factor=0.5, stock_sub=False)
            else:
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) < 5:
            if (vix > activate_option_vix) and (vix > self.previous_vix):
                self.clear_all_stocks()
                self.construct_put(max_dte, open_strike, delta_factor=0.5, stock_sub=False)

        # 检查仓位结果为Option仓位。检查VIX后，决定继续持有option并坚持rebalance，还是清掉option换成股票
        elif len(security) > 5:
            if (vix > activate_option_vix) and (vix > self.previous_vix):
                # 查看market condition，决定是否需要rebalance
                current_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
                condition_2 = (current_price - self.reference_price) / self.reference_price > rebalance_strike_u
                condition_3 = (current_price - self.reference_price) / self.reference_price < rebalance_strike_l

                condition_4 = False  # contract 第二天是否消失
                # 检查第二天是否有contract
                security_list = self.positions.SecuritySymbol.values.tolist()

                today_index = self.date_range.index(self.current_dt)
                next_day_index = today_index + 1
                next_day = self.date_range[next_day_index]
                try:
                    for security in security_list:
                        tp.quote_option_symbol(self.option_table, security, next_day)
                except Exception as error:
                    if f'{error}' == 'contract_error':
                        condition_4 = True
                    else:
                        pass

                if condition_1 or condition_2 or condition_3 or condition_4:
                    print(f'rebalanced')
                    print(f'condition_1, condition_2, condition_3, condition_4')
                    print(f'{condition_1}, {condition_2}, {condition_3}, {condition_4}')
                    self.rebalance_flag = 1
                    self.opt_substitution_flag = 0
                    # 先清掉option仓位
                    self.clear_all_options()
                    # 再重新建立合适的仓位
                    self.construct_put(max_dte, open_strike, delta_factor=0.5, stock_sub=False)
            else:
                self.clear_all_options()
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.rebalance_flag = 0

            # else:
            #     # check 是call还是put
            #     if self.positions.loc[security, 'Type'] == 'call':
            #         if vix > self.previous_vix:
            #             self.clear_all_options()
            #             self.construct_put(max_dte, open_strike)
            #         else:
            #             condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
            #             condition_4 = False  # contract 第二天是否消失
            #             # 检查第二天是否有contract
            #             today_index = self.date_range.index(self.current_dt)
            #             next_day_index = today_index + 1
            #             next_day = self.date_range[next_day_index]
            #             try:
            #                 tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
            #             except Exception as error:
            #                 if f'{error}' == 'contract_error':
            #                     condition_4 = True
            #             if condition_1 or condition_4:
            #                 print(f'rebalanced')
            #                 print(f'condition_1, condition_4')
            #                 print(f'{condition_1}, {condition_4}')
            #                 self.rebalance_flag = 1
            #                 self.opt_substitution_flag = 0
            #                 # 先清掉option仓位
            #                 self.clear_all_options()
            #                 # 再重新建立合适的仓位
            #                 self.construct_call(max_dte, open_strike)
            #
            #     elif self.positions.loc[security, 'Type'] == 'put':
            #         if vix > self.previous_vix:
            #             condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
            #
            #             condition_4 = False  # contract 第二天是否消失
            #             # 检查第二天是否有contract
            #             today_index = self.date_range.index(self.current_dt)
            #             next_day_index = today_index + 1
            #             next_day = self.date_range[next_day_index]
            #             try:
            #                 tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
            #             except Exception as error:
            #                 if f'{error}' == 'contract_error':
            #                     condition_4 = True
            #
            #             if condition_1 or condition_4:
            #                 print(f'rebalanced')
            #                 print(f'condition_1, condition_4')
            #                 print(f'{condition_1}, {condition_4}')
            #
            #                 self.rebalance_flag = 1
            #                 self.opt_substitution_flag = 0
            #                 # 先清掉option仓位
            #                 self.clear_all_options()
            #                 # 再重新建立合适的仓位
            #                 self.construct_put(max_dte, open_strike)
            #
            #         else:
            #             self.clear_all_options()
            #             self.construct_call(max_dte, open_strike)

        self.previous_vix = vix
        self.update_position_param()
