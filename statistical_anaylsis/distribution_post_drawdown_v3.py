from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
import numpy as np
from playsound import playsound
import importlib
from backtest_trading_system import trading_tools
from statsmodels.stats.descriptivestats import describe
from scipy import stats
from tqdm import tqdm

"""
本分析的目标是验证能否通过在回撤的时候，介入市场，来改变收益（log return）的分布
基础想法与经典有效市场或者马尔科夫过程不同，我们认为return不是统计学上的IID，时间序列上，前面的分布会对后续分布产生影响。
我们在某个回撤幅度下，介入市场，记录未来一段时间内的收益分别情况（样本）。然后，我们统计整个时间段内的收益分别情况（总体），然后对比样本分布和总体分布的区别。

具体执行情况如下：假设从某一天t2开始，我们观察前面一段时间观察窗口内的收益情况（t1 - t2），对比今天t2这个价位跟前面观察窗口内的最高价格，计算回撤幅度。
如果回撤幅度达到预期要求，例如回撤10%，我们买入，并持有一段时间到t3。然后我们统计持有的这段时间内（t3-t2）的每日收益分布情况，做出直方图，计算出描述性统计数据。
但是仅仅一次取样，样本量可能很小，所以一次取样后，上述过程从当前t2+1重新开始。t1 t2 都更新到t2+1。（跟v2版算法的主要区别就在这里。）多次取样，将样本汇总到一起，然后做出直方图，计算描述性统计数据。
然后我们统计整个时间段内的日收益，做出总体直方图，计算描述性统计数据。
然后比较样本直方图和整体直方图。

如果将drawdown设置为0，会触发control，每一个时间点都会取样。
从结果来看，KS test pvalue = 1， 复合预期。
"""

def distribution_analysis(output_folder, param_df, initial_settings):
    """
    :param output_folder_path:
    :param param_df: 第一个参数，previous_rolling_window, 第二个参数after_rolling_window，第三个回撤幅度
    :param initial_settings:
    :return:
    """
    context = tp.Context()

    context.initialize(**initial_settings)

    # 计算benchmark的performance指标
    context.generate_benchmark_netvalue()
    netvalues = context.benchmark_netvalue.copy()
    # netvalues = pd.read_csv('E:\\Strategy_output\\distribution_analysis\\spy_monte_carlo\\Ito_process_mento_carlo_spy_param.csv')
    netvalues.reset_index(inplace=True)
    day_counts = len(netvalues.iloc[:, 0])

    k = 0

    for benchmark in context.benchmark:
        print(f'now processing the {k + 1}th benchmark {benchmark}')
        k += 1

        population_price = netvalues[benchmark].copy()
        population_log_return = np.log(population_price) - np.log(population_price.shift(1))
        population_log_return.drop(population_log_return.head(1).index, inplace=True)
        pop_hist, bin_edges = np.histogram(population_log_return, bins=100, density=True)
        pop_discrip = describe(population_log_return)
        pop_discrip.loc['previous_rolling_window'] = 0
        pop_discrip.loc['after_rolling_window'] = 0
        pop_discrip.loc['drawdown'] = 0
        pop_discrip.loc['ks_2samp'] = 0
        pop_discrip.loc['ks_2samp_pvalue'] = 0
        pop_discrip.loc['t_stats'] = 0
        pop_discrip.loc['t_pvalue'] = 0
        pop_discrip.loc['levene_stats'] = 0
        pop_discrip.loc['levene_pvalue'] = 0

        descriptive_stats_summary = pop_discrip.copy()

        for i in tqdm(range(len(param_df))):
            param_list = param_df.iloc[i, :].tolist()
            previous_rolling_window = param_list[0]
            after_rolling_window = param_list[1]
            drawdown = param_list[2]

            sample_log_return = pd.DataFrame()
            # netvalues['Date'] = pd.to_datetime(netvalues['Date'], format='%Y-%m-%d')

            # t0:previous rolling 初始时间点, t1:previous rolling截至时间点, t2 当前时间, t3 after rolling取样截至时间
            t0 = 0  # previous rolling 初始时间点初始化
            t2 = 0  # current time
            t3 = 0  # after rolling 取样window初始化

            while t2 < day_counts:
                if t2 < 4:  # 前面3天，数据不予考虑
                    t2 += 1
                    continue
                elif t3 > day_counts:  # 如果t3超出数据范围，停止取样
                    break

                # 定义t1 = 0  # previous rolling 取样window
                if t2-t0 > previous_rolling_window:
                    t1 = t2 - previous_rolling_window
                else:
                    t1 = t0
                # 设置t3
                t3 = t2 + after_rolling_window

                netvalues_before = netvalues.loc[t1:t2, [benchmark, 'Date']]  # note that both the start and stop of the slice are included.
                max_value_before = netvalues_before[benchmark].max()
                min_value_before = netvalues_before[benchmark].min()
                netvalues_after = netvalues.loc[t2:t3, [benchmark, 'Date']]
                _daily_price = netvalues.loc[t2, benchmark]
                if drawdown < 0:
                    if _daily_price/max_value_before - 1 < drawdown:  # 判断满足取样条件，如果满足，就开始取样
                        sampling_log_return = np.log(netvalues_after[benchmark]) - np.log(netvalues_after[benchmark].shift(1))
                        netvalues_after['log_return'] = sampling_log_return
                        netvalues_after.drop(netvalues_after.head(1).index, inplace=True)
                        sample_log_return = sample_log_return.append(netvalues_after, ignore_index=True)
                        t2 += 1  # 取样后，t2更新
                        t0 = t2  # 取样后，同时reset t0 到新的数据区间
                    else:  # 如果不满足取样条件，进入下一天
                        t2 += 1
                elif drawdown > 0:
                    if _daily_price / min_value_before - 1 > drawdown:  # 判断满足取样条件，如果满足，就开始取样
                        sampling_log_return = np.log(netvalues_after[benchmark]) - np.log(netvalues_after[benchmark].shift(1))
                        netvalues_after['log_return'] = sampling_log_return
                        netvalues_after.drop(netvalues_after.head(1).index, inplace=True)
                        sample_log_return = sample_log_return.append(netvalues_after, ignore_index=True)
                        t2 += 1  # 取样后，t2更新
                        t0 = t2  # 取样后，同时reset t0 到新的数据区间
                    else:  # 如果不满足取样条件，进入下一天
                        t2 += 1
                else:
                    sampling_log_return = np.log(netvalues_after[benchmark]) - np.log(netvalues_after[benchmark].shift(1))
                    netvalues_after['log_return'] = sampling_log_return
                    netvalues_after.drop(netvalues_after.head(1).index, inplace=True)
                    sample_log_return = sample_log_return.append(netvalues_after, ignore_index=True)
                    t2 += 1  # 取样后，t2更新
                    t0 = t2  # 取样后，同时reset t0 到新的数据区间
            if sample_log_return.empty:  # 如果一直没有满足条件的回撤出现，sample_log_return可能是空的，就跳过数据输出的部分。
                descriptive_stats_summary[f'{previous_rolling_window}_{after_rolling_window}_{drawdown}'] = 0
                print(f'{previous_rolling_window}_{after_rolling_window}_{drawdown} is empty!')
                continue
            sample_hist, sample_bin_edges = np.histogram(sample_log_return['log_return'], bins=bin_edges, density=True)
            sample_descrip = describe(sample_log_return)
            # two-sample Kolmogorov-Smirnov test for equality of distribution functions
            ks_2samp_stats, ks_2samp_pvalue = stats.ks_2samp(population_log_return, sample_log_return['log_return'])
            # Calculate the T-test for the means of two independent samples of scores.
            t_stats, t_pvalue = stats.ttest_ind(population_log_return, sample_log_return['log_return'], equal_var=False)
            # Levene test for equal variances.
            leven_stats, leven_pvalue = stats.levene(population_log_return, sample_log_return['log_return'])

            sample_descrip.loc['previous_rolling_window'] = previous_rolling_window
            sample_descrip.loc['after_rolling_window'] = after_rolling_window
            sample_descrip.loc['drawdown'] = drawdown
            sample_descrip.loc['ks_2samp'] = ks_2samp_stats
            sample_descrip.loc['ks_2samp_pvalue'] = ks_2samp_pvalue
            sample_descrip.loc['t_stats'] = t_stats
            sample_descrip.loc['t_pvalue'] = t_pvalue
            sample_descrip.loc['levene_stats'] = leven_stats
            sample_descrip.loc['levene_pvalue'] = leven_pvalue


            histogram_data = pd.DataFrame({'bin_edges': bin_edges[:-1], 'sample_hist': sample_hist, 'pop_hist': pop_hist})

            descriptive_stats = pop_discrip.copy()
            descriptive_stats[f'{benchmark}_sample'] = sample_descrip['log_return']
            descriptive_stats_summary[f'{previous_rolling_window}_{after_rolling_window}_{drawdown}'] = sample_descrip['log_return']

            histogram_data.to_csv(f'{output_folder}\\{benchmark}_histogram_{previous_rolling_window}_{after_rolling_window}_{drawdown}.csv', index=False)
            descriptive_stats.to_csv(f'{output_folder}\\{benchmark}_descriptive_stats_{previous_rolling_window}_{after_rolling_window}_{drawdown}.csv', index=True)
            sample_log_return.to_csv(f'{output_folder}\\{benchmark}_sample_log_return_{previous_rolling_window}_{after_rolling_window}_{drawdown}.csv', index=True)
        descriptive_stats_summary.to_csv(f'{output_folder}\\{benchmark}_descriptive_stats_summary.csv', index=True)
    return


if __name__ == '__main__':
    scan_parameters = pd.read_csv('E:\\Strategy_output\\distribution_analysis\\'
                                  'scan_parameters_5.csv')

    # ticker_file = pd.read_csv('E:\\Mysql Databse\\stockmarket_data\\Symbol_list\\investment_clock_assets.csv')
    # symbol_list = ticker_file['Symbol'].to_list()
    symbol_list = ['QQQ', 'SPY','MTCL']
    output_folder = 'E:\\Strategy_output\\distribution_analysis\\2021-09-12_control'

    init_settings = {
        'start_date': '2011-06-01',
        'end_date': '2020-09-28',
        # 'benchmark': ['chiq'],
        'benchmark': symbol_list,

        'underlying_symbol': 'SPY',
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

    distribution_analysis(output_folder, scan_parameters, init_settings)