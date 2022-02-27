from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math
import datetime

'''
策略简介
根据vix水平，决定是持有股票，还是持有calendar spread。

vix高于threshold的时候，进入calendar spread状态。
    周一建仓calendar spread
    周五清仓
    周末不持股
'''

class StrategyContext(tp.OptionContext):

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.option_maintenance_margin = 0.1

    def handle_data(self, *args, **kwargs):
        long_dte = args[0]
        short_dte = args[1]
        open_strike = args[2]
        activate_option_vix = args[3]
        activate_stock_vix = args[4]

        self.update_position_param()

        today_dtform = datetime.datetime.strptime(self.current_dt, '%Y-%m-%d')
        today_weekday = today_dtform.weekday()
        saturday_dis = 4 - today_weekday

        weekday_range = range(0, saturday_dis+1)
        last_weekday = self.current_dt
        for weekday in weekday_range:
            test_day_dtform = today_dtform + datetime.timedelta(days=weekday)
            if test_day_dtform in self.date_range:
                pass
            else:
                previous_day_dtform = test_day_dtform - datetime.timedelta(days=1)
                last_weekday = previous_day_dtform.strftime('%Y-%m-%d')

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票还是买option
        if len(security) == 0:
            if vix > activate_option_vix:
                if self.current_dt == last_weekday:
                    pass
                else:
                    self.construct_calendar(long_dte=long_dte, short_dte=short_dte, open_strike=open_strike)
            else:
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) < 5:
            if vix > activate_option_vix:
                self.clear_all_stocks()
                if self.current_dt == last_weekday:
                    pass
                else:
                    self.construct_calendar(long_dte=long_dte, short_dte=short_dte, open_strike=open_strike)
            else:
                pass

        # 检查仓位结果为Option仓位。检查VIX后，决定继续持有option并坚持rebalance，还是清掉option换成股票
        elif len(security) > 5:
            if vix < activate_stock_vix:
                self.clear_all_options()
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

            else:
                if self.current_dt == last_weekday:
                    self.clear_all_options()
                else:
                    condition_1 = False
                    today_index = self.date_range.index(self.current_dt)
                    next_day_index = today_index + 1
                    next_day = self.date_range[next_day_index]

                    holding_option_symbol_list = self.positions.SecuritySymbol.tolist()
                    for security in holding_option_symbol_list:
                        try:
                            tp.quote_option_symbol(self.option_table, security, next_day)
                        except Exception as error:
                            if f'{error}' == 'contract_error':
                                condition_1 = True
                                self.contract_disappear_flag = 1
                            else:
                                pass
                    if condition_1:
                        print(f'rebalanced')
                        print(f'condition_1')
                        print(f'{condition_1}')
                        self.rebalance_flag = 1
                        self.opt_substitution_flag = 0
                        # 先清掉option仓位
                        self.clear_all_options()
                        self.construct_calendar(long_dte=long_dte, short_dte=short_dte, open_strike=open_strike)
                    else:
                        pass
        self.update_position_param()




