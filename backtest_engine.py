from backtest_trading_system import trading_tools as tools
import pandas as pd
from playsound import playsound
import traceback
import math
import importlib
from tqdm import tqdm


def backtest(strategy_name, param_df, output_folder_path, initial_settings):

    # 根据输入的strategy name，导入相应的策略module
    strategy_module = importlib.import_module(strategy_name)

    # playsound('E:\\voice\\nuclear_launch_detected.wav')

    context = strategy_module.StrategyContext()
    context.initialize(**initial_settings)

    # 先准备好要接受结果的dataframe和list
    backtest_results_df = param_df.copy()
    annual_return_list = []  # 作图的时候，用来统计高的annual return，以确定作图scale

    # 计算benchmark的performance指标  return，sharpe，MMD，并填入backtest_results dataframe相应的列
    context.generate_benchmark_netvalue()
    benchmark_netvalue_df = context.benchmark_netvalue
    for benchmark in context.benchmark:
        benchmark_netvalue = context.benchmark_netvalue[benchmark]

        # backtest_results_df[f'{benchmark}AnnualReturn'], backtest_results_df[f'{benchmark}SharpRatio'], backtest_results_df[f'{benchmark}MDD'] = \
        #     context.benchmark_performance(benchmark)
        benchmark_performance_elements = tools.evaluation_netvalue_performance(benchmark_netvalue)
        backtest_results_df[f'{benchmark}AnnualReturn'] = benchmark_performance_elements[0]
        backtest_results_df[f'{benchmark}SharpRatio'] = benchmark_performance_elements[1]
        backtest_results_df[f'{benchmark}MDD'] = benchmark_performance_elements[4]

        # 把这个benchmark的return填入annual_return_list第一位置
        annual_return_list.insert(0, backtest_results_df.loc[0, f'{benchmark}AnnualReturn'])

    # 计算策略中每一套参数带来的净值序列、account_status_log, position_log，并输出，作图
    for i in tqdm(range(len(param_df))):
        context = strategy_module.StrategyContext()
        context.initialize(**initial_settings)
        context.benchmark_netvalue = benchmark_netvalue_df # 将上面计算的benchmark netvalue df 传入新建的class中，避免重复计算
        day_counts = context.day_counts
        k = 0
        param_list = param_df.iloc[i, :].tolist()
        try:
            for date in context.date_range[0:-2]:
                k += 1
                context.elapsed_trade_days = k
                # print(f'this is{i}th scenario {k}th day in {day_counts} trading days')
                context.current_dt = date
                try:
                    context.handle_data(*param_list, **initial_settings)
                    context.update_account_status_log()
                except Exception as error:
                    traceback.print_exc()
                    if f'{error}' == 'Delta_error':
                        context.update_account_status_log()
                        print('we passed a Delta Error and continued to the next day in current scenario')
                        continue
                    elif f'{error}' == 'Strike_error':
                        print('we passed a strike Error and continued to the next day in current scenario')
                        continue
                    elif f'{error}' == 'option_buying_power_depleted':
                        print('break the current scenario goto the next scenario')
                        break

                    elif f'{error}' == 'stock_buying_power_depleted':
                        print('break the current scenario goto the next scenario')
                        break

                    else:
                        # playsound('E:\\voice\\landing_sequence_interrupted.wav')
                        # plan = input('what to do next: break or continue?\n'
                        #              'break: break the current scenario goto the next scenario or \n'
                        #              'continue: continue to the next day in current scenario')
                        plan = 'continue'
                        if plan == 'break':
                            break
                        if plan == 'continue':
                            continue
        except Exception as error:
            playsound('E:\\voice\\landing_sequence_interrupted.wav')
            traceback.print_exc()
            print(f'{error}')
            plan = input('what to do next: break or continue? \n'
                         'break: break the scenario loop and stop at current scenario or \n'
                         'continue: pass the current scenario and continue the scenario loop?')
            if plan == 'break':
                break
            if plan == 'continue':
                continue

        context.position_log.to_csv(f'{output_folder_path}\\position_log_{param_list}.csv', index=False)

        context.trade_log.to_csv(f'{output_folder_path}\\trade_log_{param_list}.csv', index=False)

        # 计算一套策略参数下的performance指标：return，sharpe，MMD，并计入结果表格，输出
        performance_components = tools.evaluation_netvalue_performance(context.account_status_log['PortfolioNetValue'])

        backtest_results_df.loc[i, 'PortfolioAnnualReturn'] = performance_components[0]
        backtest_results_df.loc[i, 'PortfolioSharpeRatio'] = performance_components[1]
        backtest_results_df.loc[i, 'PortfolioSortinoRatio'] = performance_components[5]
        backtest_results_df.loc[i, 'PortfolioAnnualLogProfit'] = performance_components[2]
        backtest_results_df.loc[i, 'PortfolioAnnualStd'] = performance_components[3]
        backtest_results_df.loc[i, 'MDD'] = performance_components[4]
        backtest_results_df.loc[i, 'StartDate'] = context.start_date
        backtest_results_df.loc[i, 'EndDate'] = context.end_date
        backtest_results_df.loc[i, 'TradingDays'] = len(context.account_status_log['PortfolioNetValue'])

        backtest_results_df.to_csv(f'{output_folder_path}\\backtest_results.csv', index=False)

        # #####所有的计算完成后，将benchmark_netvalue时间序列并入策略跑出来的account_status_log时间序列
        context.account_status_log = pd.merge(context.account_status_log, context.benchmark_netvalue, on='Date', how='left')
        # 专门为MACD写的内容，如果有MACD study，把MACD数据放到 account_status_log里
        if not context.stock_with_macd.empty:
            context.account_status_log = pd.merge(context.account_status_log, context.stock_with_macd, on='Date', how='left')
        # 输出account_status_log
        context.account_status_log.set_index('Date', drop=False, inplace=True)
        context.account_status_log.to_csv(f'{output_folder_path}\\account_status_log_{param_list}.csv', index=False)

        # 将结果作图
        width = math.ceil(day_counts / 250) * 8

        annual_return_list.insert(0, performance_components[0])
        abs_annual_return_list = [abs(x) for x in annual_return_list]
        height = math.ceil(max(abs_annual_return_list)/100 * day_counts / 250) * 6

        plot_line_columns = context.benchmark.copy()
        plot_line_columns.insert(0, 'PortfolioNetValue')
        plot_scatter_flags = initial_settings['plot_scatter_flags']
        strategy_clean_name = strategy_name.split('.')[-1]  # 取策略名称用于作图，把前面的module和路径去掉。
        param_list.append(strategy_clean_name)
        tools.export_plot(output_folder_path,
                          title=param_list,
                          width=width,
                          height=height,
                          data=context.account_status_log,
                          plot_line_columns=plot_line_columns,
                          plot_scatter_flags=plot_scatter_flags
                          )
    return
