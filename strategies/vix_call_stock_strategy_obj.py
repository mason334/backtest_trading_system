from backtest_trading_system import trading_platform_with_option_support as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
动态股票期权替换策略，交易期间根据VIX水平，调整仓位是option还是股票。
股票持仓的时候，可以在交易参数中设定，是否使用杠杆。

理由：期权主要功能体现在抗跌上，如果不出现大跌，option策略在不加杠杆的情况下很难跑赢大盘或者underlying。

建仓
    选择特定的股票，定好持有股票的数量。
Rebalance
    持续监控VIX水平，如果高于某个水平，就启用long call 策略,知道VIX降低到某个水平，或者股价降低到某个水平。
    然后清空call仓位，回到持股状态。
long call 策略
    选择特定的档期、strike的call，
    call数量：根据全仓持股的数量，计算出应该买入的call数量
    call rebalance：3个主要条件，
        1 特定的DTE到达
        2 股价上升到一定幅度
        3 股价下降到一定幅度
'''


class StrategyContext(tp.OptionContext):

    def handle_data(self, *args, **kwargs):
        max_dte = args[0]
        rebalance_DTE = args[1]
        open_strike = args[2]
        rebalance_strike_u = args[3]
        rebalance_strike_l = args[4]
        activate_option_vix = args[5]
        activate_stock_vix = args[6]

        self.update_position_param()

        vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空。后续检查VIX后，决定买股票还是买option
        if len(security) == 0:
            if vix > activate_option_vix:
                self.construct_call(max_dte, open_strike)
            else:
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        # 检查仓位结果为股票仓位。检查VIX后，决定继续持有股票不动,还是清掉股票换成option
        elif len(security) < 5:
            if vix > activate_option_vix:
                self.clear_all_stocks()
                self.construct_call(max_dte, open_strike)
            else:
                pass

        # 检查仓位结果为Option仓位。检查VIX后，决定继续持有option并坚持rebalance，还是清掉option换成股票
        elif len(security) > 5:
            if vix < activate_stock_vix:
                self.clear_all_options()
                stock_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                amount = round(self.equity / stock_price) * self.leverage
                self.enter_stock_order(self.underlying_symbol, stock_price, amount)
                self.opt_substitution_flag = 0

            else:
                # 查看market condition，决定是否需要rebalance
                current_price = tp.quote_stock_from_opt_mrk(self.option_table, self.current_dt)
                condition_1 = self.positions.loc[self.last_used_optionsymbol, 'DTE'] <= rebalance_DTE
                condition_2 = (current_price - self.reference_price) / self.reference_price > rebalance_strike_u
                condition_3 = (current_price - self.reference_price) / self.reference_price < rebalance_strike_l

                condition_4 = False  # contract 第二天是否消失
                # 检查第二天是否有contract
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

                if condition_1 or condition_2 or condition_3 or condition_4:
                    print(f'rebalanced')
                    print(f'condition_1, condition_2, condition_3, condition_4')
                    print(f'{condition_1}, {condition_2}, {condition_3}, {condition_4}')

                    self.rebalance_flag = 1
                    # 先清掉option仓位
                    self.clear_all_options()
                    # 再重新建立合适的仓位
                    self.construct_call(max_dte, open_strike)
                else:
                    pass

        self.update_position_param()


# def backtest(param_df, output_folder_path, initial_settings):
#     playsound('E:\\voice\\nuclear_launch_detected.wav')
#     context = StrategyContext()
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
#         context = StrategyContext()
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


