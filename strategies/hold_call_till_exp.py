from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
静态期权策略，交易期间全部持有期权。
建仓
    选择特定的档期、strike的call，
    call数量：根据全仓持股的数量，计算出应该买入的call数量
    rebalance：3个主要条件，
        1 特定的DTE到达
        2 股价上升到一定幅度
        3 股价下降到一定幅度
        
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

        # 检查option position是否为空，如果为空，建仓call option
        opt_position = len(self.positions.Type.dropna())
        if opt_position == 0:
            self.clear_all_stocks()
            self.construct_call(max_dte, open_strike)

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
                self.construct_call(max_dte, open_strike)

        self.update_position_param()