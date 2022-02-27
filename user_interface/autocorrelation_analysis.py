from statsmodels.tsa.stattools import acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from backtest_trading_system import trading_platform_stock_only as tp
import traceback

def autocorrelation_analysis(output_folder_path, initial_settings, lag):
    context = tp.Context()
    context.initialize(**initial_settings)

    # 计算benchmark的performance指标
    multi_OLS_results = pd.DataFrame()
    context.generate_benchmark_netvalue()
    error_symbol_list = list()
    i = 0
    for benchmark in context.benchmark:
        print(f'now processing the {i+1}th benchmark')
        try:
            time_series = pd.DataFrame()
            symbol_and_type = tp.check_symbol_and_type(benchmark)

            # 建立用于autocorrelation analysis的数据表
            time_series['netvalue'] = context.benchmark_netvalue[benchmark]
            time_series['daily_return'] = time_series['netvalue'].pct_change(1)
            if benchmark == 'VIX':
                time_series['daily_return'] = time_series['netvalue']
            time_series['abs_daily_return'] = abs(time_series['daily_return'])
            # time_series['weekly_return'] = time_series['netvalue'].pct_change(6)
            # time_series['monthly_return'] = time_series['netvalue'].pct_change(21)
            for l in range(lag):
                time_series[f'abs_daily_lag_{l+1}'] = time_series['abs_daily_return'].shift(l+1)
            time_series.dropna(axis=0, inplace=True)

            # 输出ACF、PACF图
            f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
            plot_acf(time_series['abs_daily_return'], lags=50, ax=ax1)
            plot_pacf(time_series['abs_daily_return'], lags=50, ax=ax2)
            plt.savefig(f'{output_folder_path}\\{benchmark}_{context.start_date}_{context.end_date}_AR.jpg', dpi=300)
            f.clear()
            plt.close(f)

            # 多元线性回归分析，找出R-squared，确认autocorrelation对于未来的解释度
            v_independent = time_series.drop(['netvalue', 'daily_return', 'abs_daily_return'], axis=1)
            v_independent_constant = sm.add_constant(v_independent)
            v_dependent = time_series['abs_daily_return']
            ar_model = sm.OLS(v_dependent, v_independent_constant).fit()
            ar_model_summary_2 = ar_model.summary2()
            OLS_results = ar_model_summary_2.tables[0]
            OLS_coefficients = ar_model_summary_2.tables[1]
            OLS_results.to_csv(f'{output_folder_path}\\{benchmark}_{context.start_date}_{context.end_date}_OLS_results.csv')
            OLS_coefficients.to_csv(f'{output_folder_path}\\{benchmark}_{context.start_date}_{context.end_date}_OLS_coefficient.csv')

            # 将多元线性回归分析得到的R-squared放入总结表格中
            multi_OLS_results.loc[i, 'Symbol'] = symbol_and_type[0]
            multi_OLS_results.loc[i, 'Type'] = symbol_and_type[1]
            multi_OLS_results.loc[i, 'R-squared'] = OLS_results.iloc[6, 1]
            multi_OLS_results.loc[i, 'lag'] = lag
            multi_OLS_results.loc[i, 'StartDate'] = context.start_date
            multi_OLS_results.loc[i, 'EndDate'] = context.end_date

        except Exception as error:
            traceback.print_exc()
            error_symbol_list.insert(-1, benchmark)
        i += 1
        multi_OLS_results.to_csv(f'{output_folder_path}//multi_OLS_results.csv')

if __name__ == '__main__':
    # ticker_file = pd.read_csv('E:\\Mysql Databse\\stockmarket_data\\Symbol_list\\sp500_ndx_sox_etf_20201004.csv')
    # symbol_list = ticker_file['Symbol'].to_list()
    symbol_list = ['MTCL']
    output_folder = 'E:\\Strategy_output\\autocorrelation_analysis\\mtcl_201001_202005'

    init_settings = {
        'start_date': '2010-01-05',
        'end_date': '2020-05-29',
        # 'benchmark': ['chiq'],
        'benchmark': symbol_list,

        'underlying_symbol': 'mtcl',
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
    autocorrelation_analysis(output_folder, init_settings, 5)