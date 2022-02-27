from backtest_trading_system.trading_tools import *
import ta
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()


# 每次执行handle_data时需要调用的数据，每次执行handle_data后会update里面部分数据。
class Context:
    def __init__(self):

        # 交易时间相关属性
        self.start_date = None
        self.end_date = None
        self.current_dt = None
        self.date_range = None
        self.DTE = None
        self.day_counts = 0
        self.elapsed_trade_days = 0  # 用于记录目前经历过了多少个交易日

        # 购买力和保证金相关的属性
        self.initial_cash = 0
        self.cash = 0
        self.cash_from_short_selling = 0
        self.total_cash = 0
        self.loan = 0
        self.total_value = None
        self.positions_value = 0  # 持仓市值
        self.equity = 0
        self.available_funds = 0  # long option参考的值
        self.stock_buying_power = 0  # long or short stock参考的 buying power
        self.option_short_power = 0  # short option 参考的buying power
        self.positions_delta = 0
        self.margin = None
        self.returns = None
        self.option_maintenance_margin = 0.5  # 隔夜保证金占做空option underlying价值的百分比
        self.stock_maintenance_margin = 0.5  # 隔夜保证金占stock净资产的百分比
        self.maintenance_requirement = 0  # 隔夜保证金的金额

        # 交易费用计算用的属性
        self.option_commission = 0.75
        self.stock_commission = 0.002
        self.mini_stock_commission = 1
        self.total_transaction_cost = 0

        # 交易和账户记录用属性
        self.position_log = pd.DataFrame()
        self.trade_log = pd.DataFrame(columns=['Date', 'SecuritySymbol', 'Amount', 'Price', 'UnderlyingPrice',
                                               'Proceeds', 'TransactionCost', 'OverMargin'])
        # account status log 写入的时候，index 是当天的日期，string格式
        self.account_status_log = pd.DataFrame(columns=['Date', 'EquityValue', 'Profit', 'PortfolioNetValue',
                                                        'Cash', 'Loan', 'MaintenanceRequirement', 'TotalTransactionCost',
                                                        'RebalanceFlag', 'StockPositionFlag', 'OptSubstitutionFlag',
                                                        'OptPositionFlag', 'ContractDisappearFlag'])
        # positions dataframe 的index是 security symbol, 在写入的时候就是这样写入的
        self.positions = pd.DataFrame(columns=['Date', "SecuritySymbol", 'Option', 'Amount', 'CostBasis', 'CurrentPrice', 'UnderlyingSymbol',
                                               'UnderlyingPrice',
                                               'Type', "DTE", "Strike", "Delta", "Gamma", 'MaintenanceRequirement'])

        # error和特殊处理的操作flag， 通过在account_status_log里面加入标记列，如果标记为1，计入当时的equity值
        self.rebalance_flag = 0  # 标记后，立刻归零
        self.opt_substitution_flag = 0  # 标记后，一直有效，知道系统主动改变
        self.contract_disappear_flag = 0  # 标记后，立刻归零
        self.heavy_position = 0  # 用于标记是否通过excercise option导致仓位增加，1表示增加，0表示没有增加

        # 对账户状态做出标记
        self.buy_dip_status = 0  # 标记后，一直有效，知道系统主动改变
        self.defend_status = 0  # 标记后，一直有效，知道系统主动改变

        # 交易执行相关的属性设置
        self.underlying_symbol = None
        self.underlying_symbol_2 = None
        self.last_used_optionsymbol = None
        self.option_table = None
        self.option_table_2 = None
        self.benchmark = []
        self.benchmark_init_price = {}
        self.benchmark_netvalue = pd.DataFrame()
        self.target_delta = 1
        self.option_type = None
        self.current_strategy = None
        self.reference_price = 0
        self.leverage = 1

        self.stock_with_macd = pd.DataFrame()

    def initialize(self, **kwargs):
        """
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
        """

        # 初始化时间，交易时间区间仅包含交易日
        self.start_date = kwargs['start_date']  # 最早到15年1月2日
        self.end_date = kwargs['end_date']  # nvda最晚到19年6月20日 spx最晚到19-05-29 aapl最晚到19-06-09
        query = f'SELECT * FROM spx'
        spx = database.df_mysql_query(query)
        spx.set_index('Date', drop=False, inplace=True)
        self.date_range = spx.loc[self.start_date: self.end_date, 'Date'].tolist()
        self.day_counts = len(self.date_range)

        # 初始化benchmark, 计算出在交易期间，benchmark的netvalue，输出dataframe
        # print('Start to initialize benchmark.\n')

        self.underlying_symbol = kwargs['underlying_symbol']
        self.option_table = kwargs['option_table']
        self.benchmark = kwargs['benchmark']

        # for stock in self.benchmark:
        #     self.benchmark_init_price[stock] = quote_stock(stock, self.start_date)
        # self.benchmark_netvalue = pd.DataFrame(columns=self.benchmark)
        #
        # for day in self.date_range:
        #     self.benchmark_netvalue.loc[day, 'Date'] = day
        #     for benchmark in self.benchmark:
        #         bench_price = quote_stock(benchmark, day)
        #         bench_net_value = bench_price / self.benchmark_init_price[benchmark]
        #         self.benchmark_netvalue.loc[day, benchmark] = bench_net_value

        # print('Benchmark initialization successful.\n')

        # 初始化交易参数
        self.option_type = "call"
        self.reference_price = 0
        self.leverage = kwargs['leverage']
        self.stock_maintenance_margin = kwargs['stock_maintenance_margin']
        self.option_maintenance_margin = kwargs['option_maintenance_margin']

        # 根据underlying，初始化资金规模
        self.target_delta = kwargs['target_delta']
        _cash = quote_stock(self.underlying_symbol, self.start_date) * 100 * self.target_delta
        self.cash = _cash
        self.initial_cash = _cash

        # 初始化MACD 指标
        self.stock_with_macd = get_full_data_from_sql_tock(self.underlying_symbol)
        _macd = ta.trend.MACD(self.stock_with_macd["Adj Close"])
        self.stock_with_macd["MACD"] = _macd.macd()
        self.stock_with_macd["MACD_Signal"] = _macd.macd_signal()
        self.stock_with_macd["MACD_Histogram"] = _macd.macd_diff()
        self.stock_with_macd.set_index('Date', drop=True, inplace=True)

    # 新的一天开始、结束、以及开单的时候都要刷新仓位表里Current price 及其后面的参数，计算当前position的delta、DTE、购买力等参数
    def update_position_param(self):
        _pos_delta = 0

        self.positions['Date'] = self.current_dt  # 如果是空仓，这句code没有任何作用
        # #################刷新position 参数#############################################
        for security in self.positions.SecuritySymbol:
            self.positions.loc[security, 'CurrentPrice'] = quote_stock(security, self.current_dt)
            _pos_delta += self.positions.loc[security, 'Amount']  # 找到仓位里面的amount
            _underlying_price = self.positions.loc[security, 'UnderlyingPrice']
            _amount = self.positions.loc[security, 'Amount']
            self.positions.loc[security, 'MaintenanceRequirement'] = abs(_amount) * self.positions.loc[security, 'CurrentPrice'] * \
                                                                     self.stock_maintenance_margin
        # ############刷新portfolio 参数####################################################
        self.positions_delta = _pos_delta
        self.maintenance_requirement = self.positions['MaintenanceRequirement'].sum()

        # for security in self.positions.SecuritySymbol:
        #     if len(security) > 5:  # 刷新总position的参数DTE
        #         self.DTE = self.positions.loc[security, 'DTE']
        #         break

        # 计算持仓市值
        _pos_value = 0
        for security in self.positions.SecuritySymbol:
            # if len(security) > 5:  # 刷新option position的参数
            #     _amount = self.positions.loc[security, 'Amount']
            #     _current_price = self.positions.loc[security, 'CurrentPrice']
            #     _pos_value += _current_price * _amount * 100
            # else:  # 刷新stock position的参数
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

    # 每一天交易完后，记录当天的profit，账户现金、equity、保证金等，同时更新position log
    def update_account_status_log(self):
        # 登记当天performance status 数据
        self.account_status_log.loc[self.current_dt, 'Date'] = self.current_dt
        self.account_status_log.loc[self.current_dt, 'EquityValue'] = self.equity
        self.account_status_log.loc[self.current_dt, 'Profit'] = self.equity - self.initial_cash
        self.account_status_log.loc[self.current_dt, 'PortfolioNetValue'] = self.equity / self.initial_cash
        self.account_status_log.loc[self.current_dt, 'Cash'] = self.cash
        self.account_status_log.loc[self.current_dt, 'Loan'] = self.loan
        self.account_status_log.loc[self.current_dt, 'MaintenanceRequirement'] = self.maintenance_requirement
        self.account_status_log.loc[self.current_dt, 'TotalTransactionCost'] = self.total_transaction_cost

        if self.rebalance_flag == 1:
            self.account_status_log.loc[self.current_dt, 'RebalanceFlag'] = self.equity / self.initial_cash
            self.rebalance_flag = 0

        if self.opt_substitution_flag == 1:
            self.account_status_log.loc[self.current_dt, 'OptSubstitutionFlag'] = self.equity / self.initial_cash

        if self.contract_disappear_flag == 1:
            self.account_status_log.loc[self.current_dt, 'ContractDisappearFlag'] = self.equity / self.initial_cash
            self.contract_disappear_flag = 0

        if self.defend_status == 1:
            self.account_status_log.loc[self.current_dt, 'DefendStatus'] = self.equity / self.initial_cash

        if self.buy_dip_status == 1:
            self.account_status_log.loc[self.current_dt, 'BuyDipStatus'] = self.equity / self.initial_cash
        else:
            # 必须加上这个0，否则在作图的时候遇到没有buy_dip_status的情况就没有值，作图的时候没有没有值会报错。
            self.account_status_log.loc[self.current_dt, 'BuyDipStatus'] = 0

        for security in self.positions.SecuritySymbol:
            if len(security) < 8:
                self.account_status_log.loc[self.current_dt, 'StockPositionFlag'] = self.equity / self.initial_cash
            elif len(security) > 8:
                self.account_status_log.loc[self.current_dt, 'OptPositionFlag'] = self.equity / self.initial_cash

        self.position_log = pd.concat([self.position_log, self.positions.reset_index(drop=True)], ignore_index=True)

    def enter_stock_order(self, stock_symbol, underlying_price, amount):

        _over_margin = 0

        # check stock margin, 判断交易available fund是否足够
        current_amount = 0
        amount_net_increase = amount

        for security in self.positions.SecuritySymbol:
            if security == stock_symbol:
                current_amount += self.positions.loc[stock_symbol, 'Amount']
                if abs(current_amount + amount) > abs(current_amount):
                    amount_net_increase = abs(current_amount + amount) - abs(current_amount)
                else:
                    amount_net_increase = 0

        if self.available_funds < underlying_price * abs(amount_net_increase) * self.stock_maintenance_margin:
            _over_margin = 1
            ex = Exception('stock_buying_power_depleted')
            print('欲购买stock，stock_buying_power_depleted, available funds不足')

            raise ex

        # 修改持仓数据，需要判断是否已经有持仓
        if stock_symbol in self.positions['SecuritySymbol'].to_list():
            if (self.positions.at[stock_symbol, "Amount"] + amount) == 0:
                self.positions.drop(index=stock_symbol, inplace=True)
            else:
                # 更新costbasis
                old_amount = self.positions.at[stock_symbol, "Amount"]
                old_costbasis = self.positions.at[stock_symbol, "CostBasis"]
                self.positions.at[stock_symbol, "CostBasis"] = (old_amount * old_costbasis + amount * underlying_price) / (old_amount + amount)
                # 更新amount
                self.positions.at[stock_symbol, "Amount"] += amount
                # 更新current price
                self.positions.at[stock_symbol, "CurrentPrice"] = underlying_price

        else:
            self.positions.at[stock_symbol, "SecuritySymbol"] = stock_symbol
            self.positions.at[stock_symbol, "Option"] = 0
            self.positions.at[stock_symbol, "Amount"] = amount
            self.positions.at[stock_symbol, "CostBasis"] = underlying_price
            self.positions.at[stock_symbol, "CurrentPrice"] = underlying_price

        # 计算交易费用
        commission = abs(amount * self.stock_commission)
        if commission > self.mini_stock_commission:
            transaction_cost = commission
        else:
            transaction_cost = self.mini_stock_commission

        # 更新总的交易费用
        self.total_transaction_cost += transaction_cost

        # 修改现金余额
        self.cash -= transaction_cost
        if amount > 0:
            self.cash -= underlying_price * amount
            if self.cash < 0:  # 如果自有现金不够花，需要融资买入
                self.loan += -self.cash
                self.cash = 0
        else:
            self.cash -= underlying_price * amount

        # 登记新的交易记录
        new_log = dict()
        new_log['Date'] = self.current_dt
        new_log['SecuritySymbol'] = stock_symbol
        new_log['Price'] = underlying_price
        new_log['UnderlyingPrice'] = underlying_price
        new_log['Amount'] = amount
        new_log['Proceeds'] = -amount * new_log['Price']
        new_log['TransactionCost'] = -transaction_cost
        new_log['OverMargin'] = _over_margin

        self.trade_log = pd.concat([self.trade_log, pd.DataFrame([new_log])], ignore_index=True, sort=False)

    def clear_stock(self, stock_symbol):
        self.update_position_param()
        for security in self.positions.SecuritySymbol:
            if security == stock_symbol:
                amount = -self.positions.loc[stock_symbol, 'Amount']
                price = quote_stock(stock_symbol, self.current_dt)
                self.enter_stock_order(stock_symbol, price, amount)

    def clear_all_stocks(self):
        self.update_position_param()
        for security in self.positions.SecuritySymbol:
            if len(security) < 8:
                self.clear_stock(security)

    def generate_benchmark_netvalue(self):
        '''
        根据context里面的benchmark symbol，从database -> stockmarket 里面读取数据，计算netvalue，装入context.benchmark_netvalue dataframe里面。
        :return:
        '''
        # self.benchmark_netvalue = pd.DataFrame()
        error_symbol_list = list()
        for symbol in self.benchmark:
            try:
                self.benchmark_netvalue[symbol] = generate_stock_netvalue(self.start_date, self.end_date, symbol)
            except Exception as error:
                error_symbol_list.insert(-1, symbol)
        if len(error_symbol_list) != 0:
            print(f'{error_symbol_list} netvalues are not generated')

    def benchmark_evaluation(self, benchmark_netvalue):
        annual_return, sharp_ratio = evaluation_netvalue_performance(benchmark_netvalue)
        mdd = compute_drawdown(benchmark_netvalue)
        return annual_return, sharp_ratio, mdd

    def benchmark_performance(self, benchmark_symbol):
        query = f'SELECT * FROM `{benchmark_symbol}`'
        stock_quote = database.df_mysql_query(query)
        stock_quote.set_index('Date', drop=False, inplace=True)
        netvalue = stock_quote.loc[self.start_date: self.end_date, 'Adj Close'] / stock_quote.loc[self.start_date, 'Adj Close']
        annual_return, sharp_ratio = evaluation_netvalue_performance(netvalue)
        mdd = compute_drawdown(netvalue)
        return annual_return, sharp_ratio, mdd

    def benchmark_performance_1(self, benchmark_symbol):
        netvalues = self.benchmark_netvalue[benchmark_symbol]
        annual_return, sharp_ratio = evaluation_netvalue_performance(netvalues)
        mdd = compute_drawdown(netvalues)
        return annual_return, sharp_ratio, mdd

    def new_high_stats(self, symbol):
        '''
        使用这个method前提条件是context.generate_benchmark_netvalue()已经被执行过，benchmark_netvalue这个df
        从context.benchmark_netvalue中，读取某个benchmark symbol的netvalue数据，放入一个netvalues的dataframe。
        按当天日期，按时间在当天之前或者滞后，将这个netvlaue的dataframe分为两个部分。
        如果当天close价格比当天之前dataframe的最高价格还高，当天就是新高，在新高clomn标记1，否则标记0.

        :param symbol:
        :return:
        '''
        netvalues = pd.DataFrame()
        netvalues[symbol] = self.benchmark_netvalue[symbol]
        netvalues.reset_index(inplace=True)
        netvalues['Date'] = pd.to_datetime(netvalues['Date'], format='%Y-%m-%d')
        netvalues.set_index('Date', inplace=True, drop=False)

        for _day in netvalues['Date']:
            _daily_price = netvalues.loc[_day, symbol]
            netvalues_before = netvalues.loc[(netvalues['Date']) < _day]
            max_value_before = netvalues_before[symbol].max()
            if max_value_before < _daily_price:
                netvalues.loc[_day, 'new_high'] = 1

                netvalues_after = netvalues.loc[netvalues['Date'] > _day]
                netvalues_after_smaller_than_daily_price = netvalues_after.loc[(netvalues_after[symbol]) < _daily_price]
                if netvalues_after_smaller_than_daily_price.empty:
                    netvalues.loc[_day, 'days_first_revisit'] = 0  # 新高后，后面没有出现比当前价更小的，标记为0.
                else:
                    first_revisit_date = netvalues_after_smaller_than_daily_price.iloc[0, 0]
                    days_first_revisit = first_revisit_date - _day
                    netvalues.loc[_day, 'days_first_revisit'] = days_first_revisit.days
            else:
                netvalues.loc[_day, 'new_high'] = 0 # 不是new_high, new_high 字段标记为0
                netvalues.loc[_day, 'days_first_revisit'] = np.nan # 没有新高，revisit标记为NaN


        # 计算创出new high的概率
        new_high_days = netvalues['new_high'].sum()
        total_days = netvalues['Date'].count()
        new_high_probability = new_high_days / total_days

        # 统计创出新高后，被重新跌破的概率
        new_high_df = netvalues.loc[netvalues['new_high'] > 0]
        new_high_revisited_df = netvalues.loc[netvalues['days_first_revisit'] > 0]

        # 统计跌破新高所需的平均时间
        new_high_average_revisit_days = new_high_revisited_df['days_first_revisit'].mean()

        #统计达到新高后，后面会跌破这个新高的概率
        number_of_new_high_revisited = new_high_revisited_df['Date'].count()
        new_high_revisit_probability = number_of_new_high_revisited / new_high_days

        return new_high_probability, new_high_average_revisit_days, new_high_revisit_probability, netvalues
