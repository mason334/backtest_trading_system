from backtest_trading_system import trading_platform_with_option_support as tp
from datetime import datetime
import pandas as pd
from First_simple_strategy import database
import matplotlib.pyplot as plt
import traceback


'''
策略简介
动态股票期权替换策略，根据earnings date调整是option还是股票。
理由：观察静态option策略，发现部分跳涨是发生在earnings date。

建仓
    选择特定的股票，定好持有股票的数量。
    持续监控date，如果接近earnings date，就启用long call 策略。
    一段时间后，清空call仓位，回到持股状态。
long call 策略
    选择特定的档期、strike的call，
    call数量：根据全仓持股的数量，计算出应该买入的call数量
    rebalance：3个主要条件，
        1 特定的DTE到达
        2 股价上升到一定幅度
        3 股价下降到一定幅度
        
2020/8/16 zxc update
'''

# 这个版本中，construct call的时候，如果查询到的contract delta< 0.01，直接就选择买相应档期ATM option。
# 这个版本中，construct call的时候，如果查询到的contract 第二天消失了，直接就选择买股票。
# 如果持仓call查询到的contract第二天消失了，当天就要卖掉，重新建仓call。


class StrategyContext(tp.OptionContext):

    def initialize(self, **kwargs):
        super().initialize()
        self.option_position_holding_days = 0

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        earnings_date_list = kwargs['earnings_date_list']

        self.update_position_param()

        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        today = self.date_range[today_index]
        next_day = self.date_range[next_day_index]
        today_dtform = datetime.strptime(today, '%Y-%m-%d')
        next_day_dtform = datetime.strptime(next_day, '%Y-%m-%d')

        next_3_day_index = today_index + 3
        next_3_day = self.date_range[next_3_day_index]

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查Date后，决定买股票还是买option
        if len(security) == 0:
            if next_3_day in earnings_date_list:
                self.construct_call(max_dte, open_strike)
            else:
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price)
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查Date后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) < 5:
            if next_3_day in earnings_date_list:
                self.clear_stock(self.underlying_symbol)
                self.construct_call(max_dte, open_strike)
            else:
                pass

        # 检查仓位结果为Option仓位。检查rebalance条件，还是清掉option换成股票
        elif len(security) > 5:

            self.option_position_holding_days += 1
            # self.opt_position_flag = 1
            # 查看market condition，决定是否需要rebalance
            # current_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
            condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
            # condition_2 = (current_price - self.reference_price) / self.reference_price > rebalance_strike_u
            # condition_3 = (current_price - self.reference_price) / self.reference_price < rebalance_strike_l
            condition_4 = False  # 检查第二天是否有contract
            today_index = self.date_range.index(self.current_dt)
            next_day_index = today_index + 1
            next_day = self.date_range[next_day_index]
            try:
                tp.quote_option_symbol(self.option_table, self.last_used_optionsymbol, next_day)
            except Exception as error:
                if f'{error}' == 'contract_error':
                    condition_4 = True
                else:
                    pass
            condition_5 = self.option_position_holding_days >= 10

            if condition_5:
                self.option_position_holding_days = 0

            if condition_1 or condition_4 or condition_5:
                print(f'rebalanced')
                print(f'condition_1, condition_4', 'condition_5')
                print(f'{condition_1}, {condition_4}', {condition_5})

                self.rebalance_flag = 1
                # self.opt_position_flag = 0
                # self.opt_substitution_flag = 0
                # 先清掉option仓位
                self.clear_all_options()
                # 再重新建立合适的仓位
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price)
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
            else:
                pass

        self.update_position_param()


# def initialize(trading_platform):
#     # 初始化时间，交易时间区间仅包含交易日
#     trading_platform.context.start_date = "2015-01-02"  # 最早到15年1月2日
#     trading_platform.context.end_date = "2019-06-09"  # nvda最晚到19年6月20日 spx最晚到19-05-29 aapl最晚到19-06-09
#     query = f"SELECT * FROM spx"
#     spx = database.df_mysql_query(query)
#     spx.set_index('Date', drop=False, inplace=True)
#     start_date = trading_platform.context.start_date
#     end_date = trading_platform.context.end_date
#     trading_platform.context.date_range = spx.loc[start_date: end_date, 'Date'].tolist()
#
#     # 初始化benchmark和earnings dates
#     print('Start to initialize benchmark.\n')
#
#     trading_platform.g.underlying_symbol = "aapl"
#     trading_platform.g.option_table = "aapl_option"
#     trading_platform.g.benchmark = ['aapl', 'aapl', 'aapl']
#     trading_platform.g.option_position_counts = 0
#
#     for stock in trading_platform.g.benchmark:
#         trading_platform.g.benchmark_init_price[stock] = trading_platform.quote_stock(stock, trading_platform.context.start_date)
#     bench1 = trading_platform.g.benchmark[0]
#     bench2 = trading_platform.g.benchmark[1]
#     bench3 = trading_platform.g.benchmark[2]
#     trading_platform.benchmark_netvalue = pd.DataFrame(columns=['Date', bench1, bench2, bench3])
#
#     for day in trading_platform.context.date_range:
#         trading_platform.g.benchmark_netvalue.loc[day, 'Date'] = day
#         for benchmark in trading_platform.g.benchmark:
#             bench_price = trading_platform.quote_stock(benchmark, day)
#             bench_net_value = bench_price/trading_platform.g.benchmark_init_price[benchmark]
#             trading_platform.g.benchmark_netvalue.loc[day, benchmark] = bench_net_value
#
#     print('Benchmark initialization successful.\n')
#
#     # 初始化交易参数
#     trading_platform.g.init_strike_ratio = 0
#     trading_platform.g.option_type = "call"
#     trading_platform.g.reference_price = 0
#     trading_platform.g.target_delta = 5
#
#     # 根据underlying，初始化资金规模
#     _cash = trading_platform.quote_stock_from_opt_mrk(trading_platform.g.option_table, start_date)*100*trading_platform.g.target_delta
#     trading_platform.context.cash = _cash
#     trading_platform.context.initial_cash = _cash


# def construct_call(max_dte, open_strike):
#     contract = tp.quote_option_market(self.option_table, self.option_type, max_dte, open_strike, self.current_dt)
#     contract_symbol = contract.loc[0, 'OptionSymbol']
#     today_index = self.date_range.index(self.current_dt)
#     next_day_index = today_index + 1
#     next_day = self.date_range[next_day_index]
#
#     # 检查第二天是否有contract信息，如果丢失，就不买这个contract，买股票，tp会识别stock，并标记stock position flag
#     try:
#         tp.quote_option_symbol(self.option_table, contract_symbol, next_day)
#     except Exception as error:
#         if f'{error}' == 'contract_error':
#             if len(self.positions['SecuritySymbol']) == 0:
#                 bad_symbol = contract.loc[0, 'OptionSymbol']
#                 print(f'{self.current_dt}, '
#                       f'{bad_symbol} while constructing call, contract disappeared next day,'
#                       f'program bought stock instead')
#
#                 stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
#                 tp.enter_stock_order(self.underlying_symbol, stock_price, self.target_delta * 100)
#                 return
#             else:
#                 return
#
#
#     # 检查contract delta是否有错，如果出错，就买入ATM contract,并标记opt_substitution_flag
#     if contract.loc[0, 'Delta'] < 0.01:
#         bad_symbol = contract.loc[0, 'OptionSymbol']
#         print(f'{self.current_dt}, '
#               f'{bad_symbol} while constructing call, contract delta < 0.01,'
#               f'program bought stock instead')
#
#         contract = tp.quote_option_market(self.option_table, self.option_type, max_dte, 0, self.current_dt)
#         contract.loc[0, 'Delta'] = 0.5
#         self.opt_substitution_flag = 1
#
#
#     # 通过检查后，继续
#     contract_count = round(self.target_delta / contract.loc[0, 'Delta'])
#     self.reference_price = contract.loc[0, 'UnderlyingPrice']
#     tp.enter_option_order(contract, contract_count)
#     tp.clear_stock(self.underlying_symbol)






