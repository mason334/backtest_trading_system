from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
初始状态，先买入股票。然后卖出等delta期权，参数包括max_dte, open_strike。
DTE小于rebalce dte的时候，rebalance 期权仓位。

2020/8/16 zxc update
'''


class StrategyContext(tp.OptionContext):

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        # rebalance_strike_u = args[3]
        # rebalance_strike_l = args[4]

        self.update_position_param()

        # 检查option position是否为空
        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空，买股票。
        if len(security) == 0:
            stock_price = tp.quote_stock_from_opt_mrk(self.underlying_symbol, self.current_dt)
            # amount = round(self.equity / stock_price) * self.leverage
            self.enter_stock_order(self.underlying_symbol, stock_price, self.target_delta*100)

        opt_position = len(self.positions.Type.dropna())
        if opt_position == 0:
            self.construct_call_by_amount(max_dte, open_strike, -self.target_delta, stock_sub=False)

        # 检查现有仓位DTE、或者累计涨跌幅是否满足rebalance条件: 如果一项为真，则需要卖掉，重新建仓
        else:
            # 查看market condition，决定是否需要rebalance
            # current_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
            condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
            condition_4 = False  # 检查第二天是否有contract
            today_index = self.date_range.index(self.current_dt)
            next_day_index = today_index + 1
            next_day = self.date_range[next_day_index]
            try:
                tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
            except Exception as error:
                if f'{error}' == 'contract_error':
                    condition_4 = True
                    self.contract_disappear_flag = 1

            if condition_1 or condition_4:
                print(f'rebalanced')
                print(f'condition_1, condition_4')
                print(f'{condition_1}, {condition_4}')

                self.rebalance_flag = 1
                # 先清掉option仓位
                self.clear_all_options()
                # 再重新建立合适的仓位
                self.construct_call_by_amount(max_dte, open_strike, -self.target_delta, stock_sub=False)

        self.update_position_param()