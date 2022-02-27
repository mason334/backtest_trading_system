from First_simple_strategy import trading_platform as tp
from datetime import datetime
import pandas as pd
from First_simple_strategy import database
import matplotlib.pyplot as plt


def buy_spread(delta, max_dte, strike_1, strike_dis ):
    strike_2 = strike_1 + strike_dis
    contract_1 = tp.quote_option_market(tp.g.option_table, tp.g.option_type, max_dte, strike_1, tp.context.current_dt)
    contract_2 = tp.quote_option_market(tp.g.option_table, tp.g.option_type, max_dte, strike_2, tp.context.current_dt)
    symbol_1 = contract_1.loc[0, 'OptionSymbol']
    symbol_2 = contract_2.loc[0, 'OptionSymbol']
    stk_1 = contract_1.loc[0, 'Strike']
    stk_2 = contract_2.loc[0, 'Strike']

    # 检查两个contract DTE是否一致
    if contract_1.loc[0, 'DTE'] != contract_2.loc[0, 'DTE']:
        print(f'{tp.context.current_dt}, {symbol_1}, {symbol_2} are in different DTE')
        ex = Exception(f'DTE_error')
        raise ex
    # 检查两个contract strike 距离是否正确
    elif stk_1 >= stk_2:
        print(f'{tp.context.current_dt}, {symbol_1}, {symbol_2} encountered strike problems')
        ex = Exception(f'Strike_error')
        raise ex

    # 检查contract是否有错，如果出错，跳过这一天的策略评价和交易
    elif abs(contract_1.loc[0, 'Delta']) < 0.01:
        print(f'{tp.context.current_dt}, {symbol_1} bad data, delta close to 0')
        # print(f'program passed {tp.context.current_dt}')
        ex = Exception(f'Delta_error')
        raise ex

    # elif abs(contract_2.loc[0, 'Delta']) < 0.01:
    #     print(f'{tp.context.current_dt}, {symbol_2} bad data, delta close to 0')
    #     # print(f'program passed {tp.context.current_dt}')
    #     ex = Exception(f'Delta_error')
    #     raise ex

    contract_count = round(delta / contract_1.loc[0, 'Delta'])

    # 通过检查后，继续
    tp.g.reference_price = contract_1.loc[0, 'UnderlyingPrice']
    tp.enter_option_order(contract_1, contract_count)
    tp.enter_option_order(contract_2, -contract_count)


def handle_data(*args):
    max_dte = args[0]
    strike_1 = args[1]
    strike_dis = args[2]

    delta = 1

    # 检查option position是否为空，如果为空，建仓put option
    opt_position = len(tp.context.positions.Type.dropna())
    if opt_position == 0:
        buy_spread(delta, max_dte, strike_1, strike_dis)
    else:
        if tp.context.positions.loc[tp.context.last_used_optionsymbol, 'DTE'] <= 1:
            for security in tp.context.positions['SecuritySymbol']:
                tp.clear_option(security)

            buy_spread(delta, max_dte, strike_1, strike_dis)

    tp.update_position_param()


def initialize(trading_platform):
    # 初始化时间，交易时间区间仅包含交易日
    trading_platform.context.start_date = "2015-01-02"  # 最早到15年1月2日
    trading_platform.context.end_date = "2019-06-09"  # # nvda最晚到19年6月20日 spx最晚到19-05-29 aapl最晚到19-06-09
    query = f"SELECT * FROM spy"
    spy = database.df_mysql_query(query)
    spy.set_index('Date', drop=False, inplace=True)
    start_date = trading_platform.context.start_date
    end_date = trading_platform.context.end_date
    trading_platform.context.date_range = spy.loc[start_date: end_date, 'Date'].tolist()

    # 初始化benchmark
    print('Start to initialize benchmark.\n')

    trading_platform.g.underlying_symbol = "aapl"
    trading_platform.g.option_table = "aapl_option"
    trading_platform.g.benchmark = ['aapl', 'spy', 'qqq']

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
            bench_net_value = bench_price / trading_platform.g.benchmark_init_price[benchmark]
            trading_platform.g.benchmark_netvalue.loc[day, benchmark] = bench_net_value

    print('Benchmark initialization successful.\n')

    # 根据underlying，初始化资金规模
    _cash = trading_platform.quote_stock(trading_platform.g.underlying_symbol, start_date)*100
    trading_platform.context.cash = _cash
    trading_platform.context.initial_cash = _cash

    # 初始化交易参数
    trading_platform.g.option_type = "call"
    trading_platform.g.reference_price = 0
    trading_platform.context.option_maintenance_margin = 0.01
