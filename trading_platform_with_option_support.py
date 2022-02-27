from backtest_trading_system.trading_platform_stock_only import *
import pandas as pd
from datetime import datetime, date, timedelta
import numpy as np
from backtest_trading_system import database
import matplotlib.dates as mdates
import matplotlib.ticker as tck
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

'''
继承 trading platform stock only 的 Context class
扩展 initialize method
重写以下三个method
update_position_param
clear_stock
clear_all_stocks
'''


class OptionContext(Context):
    def __init__(self):
        super().__init__()

    def initialize(self, **kwargs):
        '''
        初始化交易平台的参数，包括交易时间、交易标的、benchmark、是否使用杠杆、资金规模
        :param kwargs: 读入一个字典，里面包含所有的需要init的参数，一般情况，需要以下字段
        {
        'start_date': '2017-01-02',
        'end_date': '2019-06-20',
        'underlying_symbol': 'nvda',
        'option_table': 'nvda_option', 要使用的option在数据库中的table name
        'benchmark': ['nvda', 'tqqq'],
        'leverage': 1,
        'stock_maintenance_margin': 0.1, 对stock margin的调整
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag', 'StockPositionFlag', 'OptSubstitutionFlag']
        }
        '''
        super().initialize(**kwargs)
        # 根据underlying，初始化资金规模
        _cash = quote_stock_from_opt_mrk(self.underlying_symbol, self.start_date) * 100 * self.target_delta
        self.cash = _cash
        self.initial_cash = _cash

    # 新的一天开始、结束、以及开单的时候都要刷新仓位表里Current price 及其后面的参数，计算当前position的delta、DTE、购买力等参数
    def update_position_param(self):
        _pos_delta = 0

        self.positions['Date'] = self.current_dt  # 如果是空仓，这句code没有任何作用
        # #################刷新position 参数#############################################
        for security in self.positions.SecuritySymbol:
            if len(security) > 8:  # 刷新option position的参数
                lockon_contract = quote_option_symbol(self.option_table, security, self.current_dt)
                self.positions.loc[security, 'CurrentPrice'] = lockon_contract.at[0, 'Mark']
                self.positions.at[security, "Type"] = lockon_contract.at[0, "Type"]
                self.positions.loc[security, 'DTE'] = lockon_contract.at[0, 'DTE']
                self.positions.loc[security, 'Strike'] = lockon_contract.at[0, 'Strike']
                self.positions.loc[security, 'Delta'] = lockon_contract.at[0, 'Delta']
                self.positions.loc[security, 'Gamma'] = lockon_contract.at[0, 'Gamma']
                self.positions.loc[security, 'UnderlyingPrice'] = lockon_contract.at[0, 'UnderlyingPrice']

                _underlying_price = self.positions.loc[security, 'UnderlyingPrice']
                _delta = self.positions.loc[security, 'Delta']
                _amount = self.positions.loc[security, 'Amount']
                _pos_delta += _delta * _amount * 100

                # #### 计算持仓 option 的Maintenance Requirement，多仓是合约市值，
                if _amount > 0:
                    self.positions.loc[security, 'MaintenanceRequirement'] = abs(_amount) * lockon_contract.at[0, 'Mark'] * 100
                else:
                    self.positions.loc[security, 'MaintenanceRequirement'] = abs(
                        _amount) * _underlying_price * 100 * self.option_maintenance_margin

            else:  # 刷新stock position的参数
                self.positions.loc[security, 'CurrentPrice'] = quote_stock_from_opt_mrk(security, self.current_dt)
                _pos_delta += self.positions.loc[security, 'Amount']  # 找到仓位里面的amount
                _underlying_price = self.positions.loc[security, 'UnderlyingPrice']
                _amount = self.positions.loc[security, 'Amount']
                self.positions.loc[security, 'MaintenanceRequirement'] = abs(_amount) * self.positions.loc[security, 'CurrentPrice'] * \
                                                                         self.stock_maintenance_margin
        # ############刷新portfolio 参数####################################################
        self.positions_delta = _pos_delta
        self.maintenance_requirement = self.positions['MaintenanceRequirement'].sum()

        for security in self.positions.SecuritySymbol:
            if len(security) > 8:  # 刷新总position的参数DTE
                self.DTE = self.positions.loc[security, 'DTE']
                break

        # 计算持仓市值
        _pos_value = 0
        for security in self.positions.SecuritySymbol:
            if len(security) > 8:  # 刷新option position的参数
                _amount = self.positions.loc[security, 'Amount']
                _current_price = self.positions.loc[security, 'CurrentPrice']
                _pos_value += _current_price * _amount * 100
            else:  # 刷新stock position的参数
                _amount = self.positions.loc[security, 'Amount']
                _current_price = self.positions.loc[security, 'CurrentPrice']
                _pos_value += _current_price * _amount

        # 刷新portfolio持仓市值
        self.positions_value = _pos_value

        # 计算并刷新净资产余额
        self.equity = self.cash + self.positions_value - self.loan

        # 计算并刷新可用资金余额
        self.available_funds = self.equity - self.maintenance_requirement

        # 计算并刷新股票购买力
        self.stock_buying_power = self.available_funds / self.stock_maintenance_margin

        # 计算并刷新option 做空购买力
        self.option_short_power = self.available_funds / self.option_maintenance_margin

        # 如果账上有loan，用cash还掉loan
        if self.cash >= self.loan:
            self.cash = self.cash - self.loan
            self.loan = 0
        else:
            self.loan = self.loan - self.cash
            self.cash = 0

    def clear_stock(self, stock_symbol):
        self.update_position_param()
        for security in self.positions.SecuritySymbol:
            if security == stock_symbol:
                amount = -self.positions.loc[stock_symbol, 'Amount']
                price = quote_stock_from_opt_mrk(stock_symbol, self.current_dt)
                self.enter_stock_order(stock_symbol, price, amount)

    def clear_all_stocks(self):
        self.update_position_param()
        for security in self.positions.SecuritySymbol:
            if len(security) < 8:
                self.clear_stock(security)

    def enter_option_order(self, lockon_contract, amount):
        self.update_position_param()
        _over_margin = 0
        # 修改持仓数据*****需要判断是否已经有仓位****#####
        option_symbol = lockon_contract.at[0, 'OptionSymbol']

        if option_symbol in self.positions['SecuritySymbol'].to_list():  # 如果已有仓位，就update持仓数据的参数
            _end_amount = self.positions.at[option_symbol, "Amount"] + amount
            if abs(_end_amount) > abs(self.positions.at[option_symbol, "Amount"]):
                # ##########如果仓位上涨，需要check margin##############################
                # 判断做多 available fund是否足够
                if amount > 0:
                    if self.available_funds < lockon_contract.at[0, "Mark"] * amount * 100:
                        _over_margin = 1
                        ex = Exception('option_buying_power_depleted')
                        print('欲购买Option，available funds不足')
                        raise ex
                # 判断做空 buying power是否足够
                else:
                    if self.available_funds < lockon_contract.loc[0, 'UnderlyingPrice'] * abs(amount) * 100 * self.option_maintenance_margin:
                        _over_margin = 1
                        ex = Exception('option_buying_power_depleted')
                        print('欲做空Option，available funds不足')
                        raise ex

            if _end_amount == 0:
                self.positions.drop(index=option_symbol, inplace=True)
            else:
                # # 增加做多仓位的时候，costbasis要做相应调整
                old_amount = self.positions.at[option_symbol, "Amount"]
                old_costbasis = self.positions.at[option_symbol, "CostBasis"]
                current_price = lockon_contract.at[0, "Mark"]

                if amount > 0:
                    self.positions.at[option_symbol, "CostBasis"] = (old_amount * old_costbasis + amount * current_price) / (old_amount + amount)

                # 更新amount
                self.positions.at[option_symbol, "Amount"] += amount

        else:  # 如果没有仓位，就直接写入
            # ##########check margin##############################
            # 判断做多 available fund是否足够
            if amount > 0:
                if self.available_funds < lockon_contract.at[0, "Mark"] * amount * 100:
                    _over_margin = 1
                    ex = Exception('option_buying_power_depleted')
                    print('欲购买Option，available funds不足')
                    raise ex
            # 判断做空 buying power是否足够
            else:
                if self.available_funds < lockon_contract.loc[0, 'UnderlyingPrice'] * abs(amount) * 100 * self.option_maintenance_margin:
                    _over_margin = 1
                    ex = Exception('option_buying_power_depleted')
                    print('欲做空Option，available funds不足')
                    raise ex

            self.positions.at[option_symbol, "Amount"] = amount
            self.positions.at[option_symbol, "SecuritySymbol"] = lockon_contract.at[0, "OptionSymbol"]
            self.positions.at[option_symbol, "Option"] = 1
            self.positions.at[option_symbol, "CostBasis"] = lockon_contract.at[0, "Mark"]
            self.positions.at[option_symbol, 'UnderlyingSymbol'] = lockon_contract.at[0, 'UnderlyingSymbol']

        self.last_used_optionsymbol = lockon_contract.at[0, 'OptionSymbol']

        # 计算交易费用
        transaction_cost = abs(self.option_commission * amount)

        # 更新总的交易费用
        self.total_transaction_cost += transaction_cost

        # 修改现金数据
        self.cash -= transaction_cost
        if amount > 0:
            self.cash -= lockon_contract.at[0, "Mark"] * amount * 100
            if self.cash < 0:  # 如果自有现金不够花，需要融资买入
                self.loan += -self.cash
                self.cash = 0
        else:
            self.cash -= lockon_contract.at[0, "Mark"] * amount * 100

        # 登记新的交易记录
        new_log = dict()
        new_log['Date'] = self.current_dt
        new_log['SecuritySymbol'] = lockon_contract.at[0, 'OptionSymbol']
        new_log['Price'] = lockon_contract.at[0, 'Mark']
        new_log['UnderlyingPrice'] = lockon_contract.loc[0, 'UnderlyingPrice']
        new_log['Amount'] = amount
        new_log['Proceeds'] = -amount * new_log['Price'] * 100
        new_log['TransactionCost'] = -transaction_cost
        new_log['OverMargin'] = _over_margin
        self.trade_log = pd.concat([self.trade_log, pd.DataFrame([new_log])], ignore_index=True, sort=False)

        self.update_position_param()

    def clear_option(self, option_symbol):
        self.update_position_param()
        amount = -self.positions.loc[option_symbol, 'Amount']
        contract = quote_option_symbol(self.option_table, option_symbol, self.current_dt)
        self.enter_option_order(contract, amount)

    def clear_all_options(self):
        self.opt_substitution_flag = 0
        for security in self.positions.SecuritySymbol:
            if len(security) > 8:
                self.clear_option(security)

    def construct_call(self, max_dte, open_strike, delta_factor=1, stock_sub=True):
        """
        建仓Call仓位，所有call delta之和，等于Context.target_delta
        数据错误处理：
            如果查询到的合约在后一天消失了，买入股票instread
            如果查询到的合约delta不正常，买入ATM option，overide open_strike

        :param max_dte: 最大到期档
        :param open_strike: 建仓时指定的执行价
        :param delta_factor: 用于指定是否保持跟position delta一致。
        :param stock_sub: 指定是否在option 第二天消失的情况下，买stock
        """
        contract = quote_option_market(self.option_table, self.option_type, max_dte, open_strike, self.current_dt)
        contract_symbol = contract.loc[0, 'OptionSymbol']
        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        next_day = self.date_range[next_day_index]

        # 检查第二天是否有contract信息，如果丢失，就不买这个contract，买股票，tp会识别stock，并标记stock position flag
        try:
            quote_option_symbol(self.option_table, contract_symbol, next_day)
        except Exception as error:
            if f'{error}' == 'contract_error':
                # if len(self.positions['SecuritySymbol']) == 0:
                if stock_sub:
                    bad_symbol = contract.loc[0, 'OptionSymbol']
                    print(f'{self.current_dt}, '
                          f'{bad_symbol} while constructing call, contract disappeared next day,'
                          f'program bought stock instead')

                    stock_price = quote_stock_from_opt_mrk(self.underlying_symbol, self.current_dt)
                    self.enter_stock_order(self.underlying_symbol, stock_price, self.target_delta * 100 * self.leverage)
                    return False
                else:
                    return

        # 检查contract delta是否有错，如果出错，就买入ATM contract,并标记opt_substitution_flag
        if abs(contract.loc[0, 'Delta']) < 0.01:
            bad_symbol = contract.loc[0, 'OptionSymbol']
            print(f'{self.current_dt}, '
                  f'{bad_symbol} while constructing call, contract delta < 0.01,'
                  f'program bought stock instead')

            contract = quote_option_market(self.option_table, self.option_type, max_dte, 0, self.current_dt)
            contract.loc[0, 'Delta'] = 0.5
            self.opt_substitution_flag = 1

        # 通过检查后，继续
        contract_count = round(self.target_delta / contract.loc[0, 'Delta']) * self.leverage * delta_factor
        self.reference_price = contract.loc[0, 'UnderlyingPrice']
        self.enter_option_order(contract, contract_count)
        return True

    def construct_call_by_amount(self, max_dte, open_strike, amount, stock_sub=True):
        """
        建仓Call仓位，所有call delta之和，等于Context.target_delta
        数据错误处理：
            如果查询到的合约在后一天消失了，在stock_sub = True的情况下，买入股票instead
        :param max_dte: 最大到期档
        :param open_strike: 建仓时指定的执行价
        :param amount: 指定call的数量
        :param delta_factor: 用于指定是否保持跟position delta一致。
        :param stock_sub: 指定是否在option 第二天消失的情况下，买stock
        """
        contract = quote_option_market(self.option_table, self.option_type, max_dte, open_strike, self.current_dt)
        contract_symbol = contract.loc[0, 'OptionSymbol']
        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        next_day = self.date_range[next_day_index]

        # 检查第二天是否有contract信息，如果丢失，就不买这个contract，买股票，tp会识别stock，并标记stock position flag
        try:
            quote_option_symbol(self.option_table, contract_symbol, next_day)
        except Exception as error:
            if f'{error}' == 'contract_error':
                # if len(self.positions['SecuritySymbol']) == 0:
                if stock_sub:
                    bad_symbol = contract.loc[0, 'OptionSymbol']
                    print(f'{self.current_dt}, '
                          f'{bad_symbol} while constructing call, contract disappeared next day,'
                          f'program bought stock instead')

                    stock_price = quote_stock_from_opt_mrk(self.underlying_symbol, self.current_dt)
                    self.enter_stock_order(self.underlying_symbol, stock_price, self.target_delta * 100 * self.leverage)
                    return False
                else:
                    return False

        # 检查contract delta是否有错，如果出错，就买入ATM contract,并标记opt_substitution_flag
        # if abs(contract.loc[0, 'Delta']) < 0.01:
        #     bad_symbol = contract.loc[0, 'OptionSymbol']
        #     print(f'{self.current_dt}, '
        #           f'{bad_symbol} while constructing call, contract delta < 0.01,'
        #           f'program bought stock instead')
        #
        #     contract = quote_option_market(self.option_table, self.option_type, max_dte, 0, self.current_dt)
        #     contract.loc[0, 'Delta'] = 0.5
        #     self.opt_substitution_flag = 1

        # 通过检查后，继续
        # contract_count = round(self.target_delta / contract.loc[0, 'Delta']) * self.leverage * delta_factor
        self.reference_price = contract.loc[0, 'UnderlyingPrice']
        self.enter_option_order(contract, amount)
        return True

    def construct_calendar(self, long_dte, short_dte, open_strike):
        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        next_day = self.date_range[next_day_index]

        long_contract = quote_option_market(self.option_table, self.option_type, long_dte, open_strike, self.current_dt)

        short_contract = quote_option_market(self.option_table, self.option_type, short_dte, open_strike, self.current_dt)

        contract_list = [long_contract, short_contract]

        for contract in contract_list:
            try:
                contract_symbol = contract.loc[0, 'OptionSymbol']
                quote_option_symbol(self.option_table, contract_symbol, next_day)
            except Exception as error:
                if f'{error}' == 'contract_error':
                    if len(self.positions['SecuritySymbol']) == 0:
                        bad_symbol = contract.loc[0, 'OptionSymbol']
                        print(f'{self.current_dt}, '
                              f'{bad_symbol} while looking for call, contract disappeared next day,'
                              f'program does not construct calendar.')
                        return

        # 通过检查后，继续
        # long_contract.loc[0, 'Delta'] = 0.5
        # short_contract.loc[0, 'Delta'] = 0.5
        contract_count = round(self.target_delta / 0.5) * self.leverage
        self.enter_option_order(long_contract, contract_count)
        self.enter_option_order(short_contract, -contract_count)

    def construct_put(self, max_dte, open_strike, delta_factor=1, stock_sub=True):
        """
        建仓put仓位，所有put delta之和，等于Context.target_delta
        数据错误处理：
            如果查询到的合约在后一天消失了，不执行买入
            如果查询到的合约delta不正常，买入ATM put option，overide open_strike

        :param max_dte: 最大到期档
        :param open_strike: 建仓时指定的执行价
        :param delta_factor: 用于指定是否保持跟position delta一致。
        :param stock_sub: 指定是否在option 第二天消失的情况下，买stock

        """
        contract = quote_option_market(self.option_table, 'put', max_dte, open_strike, self.current_dt)
        contract_symbol = contract.loc[0, 'OptionSymbol']
        today_index = self.date_range.index(self.current_dt)
        next_day_index = today_index + 1
        next_day = self.date_range[next_day_index]

        # 检查第二天是否有contract信息，如果丢失，就不买这个contract，买股票，tp会识别stock，并标记stock position flag
        try:
            quote_option_symbol(self.option_table, contract_symbol, next_day)
        except Exception as error:
            if f'{error}' == 'contract_error':
                bad_symbol = contract.loc[0, 'OptionSymbol']
                print(f'{self.current_dt}, '
                      f'{bad_symbol} while constructing call, contract disappeared next day,'
                      f'program wait for the next day')
                if stock_sub:
                    stock_price = quote_stock_from_opt_mrk(self.underlying_symbol, self.current_dt)
                    self.enter_stock_order(self.underlying_symbol, stock_price,
                                           -self.target_delta * 100 * self.leverage * delta_factor)
                return False

        # 检查contract delta是否有错，如果出错，就买入ATM contract,并标记opt_substitution_flag
        if abs(contract.loc[0, 'Delta']) < 0.01:
            bad_symbol = contract.loc[0, 'OptionSymbol']
            print(f'{self.current_dt}, '
                  f'{bad_symbol} while constructing call, contract delta < 0.01,'
                  f'program bought stock instead')

            contract = quote_option_market(self.option_table, 'put', max_dte, 0, self.current_dt)
            contract.loc[0, 'Delta'] = -0.5
            self.opt_substitution_flag = 1


        # 通过检查后，继续
        contract_count = -round(self.target_delta / contract.loc[0, 'Delta']) * self.leverage * delta_factor
        self.reference_price = contract.loc[0, 'UnderlyingPrice']
        self.enter_option_order(contract, contract_count)
        return True

    def construct_straddle(self, max_dte, open_strike, delta_factor=1):
        """
        建仓Call仓位 和put仓位，所有call delta之和，等于Context.target_delta
        数据错误处理：
            如果查询到的合约在后一天消失了，买入股票instread
            如果查询到的合约delta不正常，买入ATM option，overide open_strike

        :param max_dte: 最大到期档
        :param open_strike: 建仓时指定的执行价
        :param delta_factor: 指定建仓的数量和方向
        """
        call = self.construct_call(max_dte, open_strike, stock_sub=False, delta_factor=delta_factor)
        put = self.construct_put(max_dte, open_strike, stock_sub=False, delta_factor=delta_factor)
        if call and put:
            return True
        else:
            self.clear_all_options()

    # 适用周五到期自然exercise情况，根据DTE来判断是否exercise
    # 只适用于一般的option，expire on friday。周五不是trading day时，周四提前exercise。
    def exercise_opt(self, option_symbol):
        self.update_position_param()
        friday_not_trading = 0  # 首先定义 friday的标签，供后面使用
        amount = self.positions.loc[option_symbol, 'Amount']
        lockon_contract = quote_option_symbol(self.option_table, option_symbol, self.current_dt)
        if lockon_contract.loc[0, 'DTE'] > 1:
            return 0
        elif lockon_contract.loc[0, 'DTE'] < 0:
            ex = Exception('错误，DTE<0, 有option没有在预定的日期exercise')
            print(f'{self.current_dt}, the following option error /n {option_symbol}')
            raise ex
        elif lockon_contract.loc[0, 'DTE'] == 1:
            # 查看接着的周五是否是trading day，如果不是，说明周五是holiday，周四就exercise
            today_index = self.date_range.index(self.current_dt)
            next_day_index = today_index + 1
            today = self.date_range[today_index]
            next_day = self.date_range[next_day_index]
            today_dtform = datetime.strptime(today, '%Y-%m-%d')
            next_day_dtform = datetime.strptime(next_day, '%Y-%m-%d')
            if today_dtform.weekday() == 3:
                if next_day_dtform.weekday() == 4:  # 下一个trading day是周五，今天不exercise，返回0
                    return 0
                else:  # 下一个trading day不是周五，今天需要exercise，pass后进入下一步流程
                    friday_not_trading = 1
            else:
                ex = Exception('expiration_not_friday')
                print('Expiration is not on Friday, current exercise method is not applicable to this underlying.\n')
                raise ex
        if lockon_contract.loc[0, 'DTE'] == 0 or friday_not_trading:
            print(f'now exercising option {amount} {option_symbol} on {self.current_dt}')
            current_close = quote_stock_from_opt_mrk(self.underlying_symbol, self.current_dt)

            if lockon_contract.loc[0, 'Type'] == 'call':
                if lockon_contract.loc[0, 'Strike'] > current_close:
                    self.positions.drop(index=option_symbol, inplace=True)
                else:
                    lockon_contract.loc[0, 'Mark'] = current_close - lockon_contract.loc[0, 'Strike']
                    self.enter_option_order(lockon_contract, -amount)
                    self.enter_stock_order(self.underlying_symbol, lockon_contract.loc[0, 'Strike'], amount * 100)

                    # exercise后，回调total transaction cost
                    opt_transaction_cost = abs(amount * self.option_commission)
                    stock_commission = abs(amount * 100 * self.stock_commission)
                    if stock_commission > self.mini_stock_commission:
                        stock_transaction_cost = stock_commission
                    else:
                        stock_transaction_cost = self.mini_stock_commission
                    self.cash += (opt_transaction_cost + stock_transaction_cost)
                    self.total_transaction_cost -= (opt_transaction_cost + stock_transaction_cost)

            elif lockon_contract.loc[0, 'Type'] == 'put':
                if lockon_contract.loc[0, 'Strike'] < current_close:
                    self.positions.drop(index=option_symbol, inplace=True)
                else:
                    lockon_contract.loc[0, 'Mark'] = lockon_contract.loc[0, 'Strike'] - current_close
                    self.enter_option_order(lockon_contract, -amount)
                    self.enter_stock_order(self.underlying_symbol, lockon_contract.loc[0, 'Strike'], amount * 100)

                    # exercise后，回补transaction cost
                    opt_transaction_cost = abs(amount * self.option_commission)
                    stock_commission = abs(amount * 100 * self.stock_commission)
                    if stock_commission > self.mini_stock_commission:
                        stock_transaction_cost = stock_commission
                    else:
                        stock_transaction_cost = self.mini_stock_commission
                    self.cash += (opt_transaction_cost + stock_transaction_cost)

        self.update_position_param()
        return 1

    # 强制exercise option仓位。一般用于查询不到contract信息的情况下，清理仓位。
    # 主要误差在交易费用上，这里引用的是 enter_stock_order method来处理，按交易stock的费用计算的。
    def force_exercise_opt(self, option_symbol):
        # sell for intrinsic value
        _strike = self.positions.loc[option_symbol, 'Strike']
        _spot = quote_stock(self.underlying_symbol, self.current_dt)
        _type = self.positions.loc[option_symbol, 'Type']
        _opt_count = self.positions.loc[option_symbol, 'Amount']

        if _type == 'call':
            if (_strike - _spot) > 0:
                intrinsic = 0
            else:
                intrinsic = _spot - _strike
            self.enter_stock_order(option_symbol, intrinsic, -_opt_count)

        elif _type == 'put':
            if (_strike - _spot) < 0:
                intrinsic = 0
            else:
                intrinsic = _spot - _strike
            self.enter_stock_order(option_symbol, intrinsic, -_opt_count)