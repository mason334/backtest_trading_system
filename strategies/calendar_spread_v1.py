from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
根据vix水平，决定是持有股票，还是持有calendar spread。

vix高于threshold的时候，进入calendar spread状态。
    周一建仓calendar spread
    周五清仓
    周末不持股
'''


class StrategyContext(tp.OptionContext):

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        rebalance_strike_u = args[3]
        rebalance_strike_l = args[4]

        self.update_position_param()

        # 检查option position是否为空，如果为空，建仓call option
        opt_position = len(self.positions.Type.dropna())
        if opt_position == 0:
            self.clear_all_stocks()
            self.construct_call(max_dte, open_strike)

        # 检查现有仓位DTE、或者累计涨跌幅是否满足rebalance条件: 如果一项为真，则需要卖掉，重新建仓
        # rebalance的幅度，应该是目标max DTE时间间隔的average return，需要计算，应该有个分布，这里假设是10%
        else:
            # 查看market condition，决定是否需要rebalance
            current_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
            condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
            condition_2 = (current_price - self.reference_price) / self.reference_price > rebalance_strike_u
            condition_3 = (current_price - self.reference_price) / self.reference_price < rebalance_strike_l

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

            if condition_1 or condition_2 or condition_3 or condition_4:
                print(f'rebalanced')
                print(f'condition_1, condition_2, condition_3, condition_4')
                print(f'{condition_1}, {condition_2}, {condition_3}, {condition_4}')

                self.rebalance_flag = 1
                self.opt_substitution_flag = 0
                # 先清掉option仓位
                self.clear_all_options()
                # 再重新建立合适的仓位
                self.construct_call(max_dte, open_strike)

        self.update_position_param()


# def backtest(param_df, output_folder_path, initial_settings):
#     playsound('E:\\voice\\nuclear_launch_detected.wav')
#     context = ContextCall()
#     context.initialize(**initial_settings)
#     # 计算benchmark的performance指标
#
#     backtest_results_df = param_df.copy()
#
#     annual_return_list = []
#     for benchmark in context.benchmark:
#         backtest_results_df[f'{benchmark}AnnualReturn'], backtest_results_df[f'{benchmark}SharpRatio'], backtest_results_df[f'{benchmark}MDD'] = \
#             context.benchmark_performance(benchmark)
#         annual_return_list.insert(0, backtest_results_df.loc[0, f'{benchmark}AnnualReturn'])
#
#     for i in range(len(param_df)):
#         context = ContextCall()
#         context.initialize(**initial_settings)
#         day_counts = len(context.date_range)
#         k = 0
#         param_list = param_df.iloc[i, :].tolist()
#         try:
#             for date in context.date_range[0:-2]:
#                 k += 1
#                 print(f'this is{i}th scenario {k}th day in {day_counts} trading days')
#                 context.current_dt = date
#                 try:
#                     context.handle_data(*param_list)
#                     context.update_account_status_log()
#                 except Exception as error:
#                     traceback.print_exc()
#                     if f'{error}' == 'Delta_error':
#                         context.update_account_status_log()
#                         print('we passed a Delta Error and continued to the next day in current scenario')
#                         continue
#                     elif f'{error}' == 'Strike_error':
#                         print('we passed a strike Error and continued to the next day in current scenario')
#                         continue
#                     elif f'{error}' == 'option_buying_power_depleted':
#                         print('break the current scenario goto the next scenario')
#                         break
#                     else:
#                         playsound('E:\\voice\\landing_sequence_interrupted.wav')
#                         plan = input('what to do next: break or continue?\n'
#                                      'break: break the current scenario goto the next scenario or \n'
#                                      'continue: continue to the next day in current scenario')
#                         if plan == 'break':
#                             break
#                         if plan == 'continue':
#                             continue
#         except Exception as error:
#             playsound('E:\\voice\\landing_sequence_interrupted.wav')
#             traceback.print_exc()
#             print(f'{error}')
#             plan = input('what to do next: break or continue? \n'
#                          'break: break the scenario loop and stop at current scenario or \n'
#                          'continue: pass the current scenario and continue the scenario loop?')
#             if plan == 'break':
#                 break
#             if plan == 'continue':
#                 continue
#
#         context.position_log.to_csv(f'{output_folder_path}\\position_log_{param_list}.csv', index=False)
#
#         context.trade_log.to_csv(f'{output_folder_path}\\trade_log_{param_list}.csv', index=False)
#
#         portfolio_max_drawdown = tp.compute_drawdown(context.account_status_log['PortfolioNetValue'])
#         portfolio_annual_return, portfolio_sharp_ratio = tp.compute_sharpe_ratio(context.account_status_log['PortfolioNetValue'])
#         backtest_results_df.loc[i, 'PortfolioAnnualReturn'] = portfolio_annual_return
#         backtest_results_df.loc[i, 'PortfolioSharpRatio'] = portfolio_sharp_ratio
#         backtest_results_df.loc[i, 'PortfolioMDD'] = portfolio_max_drawdown
#         backtest_results_df.to_csv(f'{output_folder_path}\\backtest_results.csv', index=False)
#
#         context.account_status_log = pd.merge(context.account_status_log, context.benchmark_netvalue, on='Date', how='outer')
#         context.account_status_log.set_index('Date', drop=False, inplace=True)
#         context.account_status_log.to_csv(f'{output_folder_path}\\account_status_log_{param_list}.csv', index=False)
#
#         # 将结果作图
#         width = math.ceil(day_counts / 250) * 8
#
#         annual_return_list.insert(0, portfolio_annual_return)
#         abs_annual_return_list = [abs(x) for x in annual_return_list]
#         height = math.ceil(max(abs_annual_return_list)/100 * day_counts / 250) * 6
#
#         plot_line_columns = context.benchmark.copy()
#         plot_line_columns.insert(0, 'PortfolioNetValue')
#         plot_scatter_flags = initial_settings['plot_scatter_flags']
#
#         tp.export_plot(output_folder_path,
#                        title=param_list,
#                        width=width,
#                        height=height,
#                        data=context.account_status_log,
#                        plot_line_columns=plot_line_columns,
#                        plot_scatter_flags=plot_scatter_flags
#                        )
#     return
