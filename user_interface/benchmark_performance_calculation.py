from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
from playsound import playsound
import importlib
from backtest_trading_system import trading_tools


def performance_evaluation(output_folder_path, initial_settings):
    context = tp.Context()
    context.initialize(**initial_settings)

    # 计算benchmark的performance指标
    benchmark_results = pd.DataFrame()
    context.generate_benchmark_netvalue()
    error_symbol_list = list()
    i = 0

    for benchmark in context.benchmark:
        print(f'now processing the {i+1}th benchmark')
        try:
            symbol_and_type = tp.check_symbol_and_type(benchmark)
            benchmark_results.loc[i, 'Symbol'] = symbol_and_type[0]
            benchmark_results.loc[i, 'Type'] = symbol_and_type[1]
            netvalue = context.benchmark_netvalue[benchmark]
            performance_components = tp.evaluation_netvalue_performance(netvalue)
            benchmark_results.loc[i, 'AnnualReturn'] = performance_components[0]
            benchmark_results.loc[i, 'SharpeRatio'] = performance_components[1]
            benchmark_results.loc[i, 'SortinoRatio'] = performance_components[5]
            benchmark_results.loc[i, 'annual_log_profit'] = performance_components[2]
            benchmark_results.loc[i, 'annual_std'] = performance_components[3]
            benchmark_results.loc[i, 'MDD'] = performance_components[4]
            benchmark_results.loc[i, 'StartDate'] = context.start_date
            benchmark_results.loc[i, 'EndDate'] = context.end_date
            benchmark_results.loc[i, 'TradingDays'] = len(netvalue)

            # # 计算新高的统计数据
            new_high_stats = context.new_high_stats(benchmark)
            benchmark_results.loc[i, 'new_high_probability'] = new_high_stats[0]
            benchmark_results.loc[i, 'new_high_average_revisit_days'] = new_high_stats[1]
            benchmark_results.loc[i, 'new_high_revisit_probability'] = new_high_stats[2]
            # export benchmark netvalue data,包括计算了new high 标记，revisit 标记
            new_high_stats[3].to_csv(f'{output_folder_path}\\{benchmark}_netvalues.csv', index=False)

        except Exception as error:
            traceback.print_exc()
            error_symbol_list.insert(-1, benchmark)
        i += 1
    benchmark_results.to_csv(f'{output_folder_path}\\{context.start_date}_{context.end_date}.csv', index=False)
    if len(error_symbol_list) != 0:
        print(f'{error_symbol_list} performance are not calculated')

    return


if __name__ == '__main__':
    ticker_file = pd.read_csv('E:\\Mysql Databse\\stockmarket_data\\Symbol_list\\investment_clock_assets.csv')
    symbol_list = ticker_file['Symbol'].to_list()
    # symbol_list = ['AAPL', 'KOL','TT']
    output_folder = 'E:\\Strategy_output\\investment_clock'

    init_settings = {
        'start_date': '2020-06-01',
        'end_date': '2020-12-31',
        # 'benchmark': ['chiq'],
        'benchmark': symbol_list,

        'underlying_symbol': 'spx',
        'underlying_symbol_2': '',
        'option_table': '',
        'option_table_2': '',
        'leverage': 1,
        'stock_maintenance_margin': 0.1,
        'option_maintenance_margin': 0.05,
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag',
                               # 'StockPositionFlag',
                               'OptSubstitutionFlag',
                               'ContractDisappearFlag'],
        'earnings_date_list': []
    }

    performance_evaluation(output_folder, init_settings)