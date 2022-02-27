from First_simple_strategy import trading_platform as tp
from datetime import datetime
import pandas as pd
from First_simple_strategy import database
import matplotlib.pyplot as plt
import traceback


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
'''

# 这个版本中，construct call的时候，如果查询到的contract delta< 0.01，直接就选择买相应档期ATM option。
# 这个版本中，construct call的时候，如果查询到的contract 第二天消失了，直接就选择买股票。
# 如果持仓call查询到的contract第二天消失了，当天就要卖掉，重新建仓call。




def handle_data(*args):
    max_dte = args[0]
    rebalance_DTE = args[1]
    open_strike = args[2]
    rebalance_strike_u = args[3]
    rebalance_strike_l = args[4]

    tp.update_position_param()


    # 检查option position是否为空，如果为空，建仓call option
    opt_position = len(tp.context.positions.Type.dropna())    
    if opt_position == 0:
        construct_call(max_dte, open_strike)

    # 检查现有仓位DTE、或者累计涨跌幅是否满足rebalance条件: 如果一项为真，则需要卖掉，重新建仓
    # rebalance的幅度，应该是目标max DTE时间间隔的average return，需要计算，应该有个分布，这里假设是10%
    else:
        # 查看market condition，决定是否需要rebalance
        current_price = tp.quote_stock_from_opt_mrk(tp.g.option_table, tp.context.current_dt)
        condition_1 = tp.context.positions.loc[tp.context.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
        condition_2 = (current_price-tp.g.reference_price)/tp.g.reference_price > rebalance_strike_u
        condition_3 = (current_price-tp.g.reference_price)/tp.g.reference_price < rebalance_strike_l
        condition_4 = False # 检查第二天是否有contract
        today_index = tp.context.date_range.index(tp.context.current_dt)
        next_day_index = today_index + 1
        next_day = tp.context.date_range[next_day_index]
        try:
            tp.quote_option_symbol(tp.g.option_table, tp.context.last_used_optionsymbol, next_day)
        except Exception as error:
            if f'{error}' == 'contract_error':
                condition_4 = True

        if condition_1 or condition_2 or condition_3 or condition_4:
            print(f'rebalanced')
            print(f'condition_1, condition_2, condition_3, condition_4')
            print(f'{condition_1}, {condition_2}, {condition_3}, {condition_4}')

            tp.context.rebalance_flag = 1
            tp.context.opt_substitution_flag = 0
            # 先清掉option仓位
            tp.clear_all_options()
            # 再重新建立合适的仓位
            construct_call(max_dte, open_strike)

    tp.update_position_param()


def initialize(trading_platform):
    # 初始化时间，交易时间区间仅包含交易日
    trading_platform.context.start_date = "2015-01-02"  # 最早到15年1月2日
    trading_platform.context.end_date = "2019-06-20"  # nvda最晚到19年6月20日 spx最晚到19-05-29 aapl最晚到19-06-09
    query = f"SELECT * FROM spx"
    spx = database.df_mysql_query(query)
    spx.set_index('Date', drop=False, inplace=True)
    start_date = trading_platform.context.start_date
    end_date = trading_platform.context.end_date
    trading_platform.context.date_range = spx.loc[start_date: end_date, 'Date'].tolist()

    # 初始化benchmark
    print('Start to initialize benchmark.\n')

    trading_platform.g.underlying_symbol = "nvda"
    trading_platform.g.option_table = "nvda_option"
    trading_platform.g.benchmark = ['nvda', 'nvda', 'nvda']

    for stock in trading_platform.g.benchmark:
        trading_platform.g.benchmark_init_price[stock] = trading_platform.quote_stock(stock, trading_platform.context.start_date)
    bench1 = trading_platform.g.benchmark[0]
    bench2 = trading_platform.g.benchmark[1]
    bench3 = trading_platform.g.benchmark[2]
    trading_platform.benchmark_netvalue = pd.DataFrame(columns=['Date', bench1, bench2, bench3])

    for day in trading_platform.context.date_range:
        trading_platform.g.benchmark_netvalue.loc[day, 'Date'] = day
        for benchmark in trading_platform.g.benchmark:
            bench_price = trading_platform.quote_stock(benchmark, day)
            bench_net_value = bench_price/trading_platform.g.benchmark_init_price[benchmark]
            trading_platform.g.benchmark_netvalue.loc[day, benchmark] = bench_net_value

    print('Benchmark initialization successful.\n')

    # 初始化交易参数
    trading_platform.g.init_strike_ratio = 0
    trading_platform.g.option_type = "call"
    trading_platform.g.reference_price = 0
    trading_platform.g.target_delta = 5

    # 根据underlying，初始化资金规模
    _cash = trading_platform.quote_stock_from_opt_mrk(trading_platform.g.option_table, start_date)*100*trading_platform.g.target_delta
    trading_platform.context.cash = _cash
    trading_platform.context.initial_cash = _cash
