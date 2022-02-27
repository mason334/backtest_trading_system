import pandas as pd
from datetime import datetime, date, timedelta
import numpy as np
from backtest_trading_system import database
import matplotlib.dates as mdates
import matplotlib.ticker as tck
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
import glob
import os

register_matplotlib_converters()


def quote_option_market(option_table_sql, type, upper_DTE, strike_ratio, date):
    # 根据option条件，找到合适的contract
    # 根据当天日期、option类型、DTE找到合适的档期，再通过strike ratio找到合适的strike

    query = f"SELECT * FROM {option_table_sql} where datadate = '{date}' and DTE <= {upper_DTE} and Type = '{type}'"
    daily_market = database.df_mysql_opt_query(query)
    # 检查是否查询到合适的结果
    if daily_market.empty:
        ex = Exception('contract_error')
        print(f'{date} quote_option_market没有在{option_table_sql} 中查询到符合条件的option合约。')
        raise ex
    realized_max_DTE = np.max(daily_market["DTE"])
    DTE_market = daily_market.query(f"DTE == {realized_max_DTE}")

    # 在档期内，根据Strike要求找到合适的合约
    underlying_price = DTE_market["UnderlyingPrice"].unique()[0]
    target_strike = underlying_price * (1 + strike_ratio)
    strike_list = DTE_market['Strike'].to_list()
    strike_list.sort()
    nearest_strike = min(strike_list, key=lambda x: abs(x - target_strike))

    # 锁定目标合约
    lockon_contract = DTE_market.query(f"Strike == {nearest_strike}")
    lockon_contract.reset_index(inplace=True, drop=True)
    return lockon_contract


def quote_option_symbol(option_table_sql, option_symbol, date):
    # 根据option代码和日期，查询行情信息
    query = f"SELECT * FROM {option_table_sql} where datadate = '{date}' and OptionSymbol = '{option_symbol}'"
    lockon_contract = database.df_mysql_opt_query(query)
    # 检查是否查询到合适的结果
    if lockon_contract.empty:
        ex = Exception('contract_error')
        print(f'{date} quote_option_symbol没有在{option_table_sql} 中查询到{option_symbol}合约')
        raise ex
    lockon_contract.reset_index(inplace=True, drop=True)
    return lockon_contract


def quote_stock_from_opt_mrk(stock_symbol, date):
    option_table_sql = stock_symbol + '_option'
    # 查询underlying 市场行情
    query = f"SELECT * FROM {option_table_sql} where datadate = '{date}' limit 1"
    lockon_contract = database.df_mysql_opt_query(query)
    #检查是否查询到合适的结果
    if lockon_contract.empty:
        ex = Exception('stock_error')
        print(f'{date} quote_stock_from_opt_mrk没有在{option_table_sql} 中查询到符合的日期')
        raise ex
    lockon_contract.reset_index(inplace=True, drop=True)
    underlying_price = lockon_contract.at[0, "UnderlyingPrice"]
    return underlying_price


def check_symbol_and_type(stock_table_sql):
    query = f"SELECT * FROM `{stock_table_sql}` limit 1"
    symbol_type = database.df_mysql_query(query).loc[0, 'Type']
    symbol = database.df_mysql_query(query).loc[0, 'Symbol']
    return symbol, symbol_type

# quote stock method主要用于计算benchmark 数据，一般交易算法，用quote stock from mrk，这样与option交易数据口径保持一致
def quote_stock(stock_table_sql, date):
    # 查询underlying 市场行情
    query = f"SELECT * FROM `{stock_table_sql}` where `date` = '{date}'"
    stock_quote = database.df_mysql_query(query)
    #检查是否查询到合适的结果
    if stock_quote.empty:
        ex = Exception('stock_error')
        print(f'{date} quote_stock没有在{stock_table_sql} 中查询到符合的日期')
        raise ex
    stock_quote.reset_index(inplace=True, drop=True)
    price = stock_quote.at[0, "Adj Close"]
    return price


# quote stock method主要用于计算benchmark 数据，一般交易算法，用quote stock from mrk，这样与option交易数据口径保持一致
def quote_vix_high(date):
    # 查询underlying 市场行情
    query = f"SELECT * FROM `vix` where `date` = '{date}'"
    stock_quote = database.df_mysql_query(query)
    # 检查是否查询到合适的结果
    if stock_quote.empty:
        ex = Exception('stock_error')
        print(f'{date} quote_stock没有在vix中查询到符合的日期')
        raise ex
    stock_quote.reset_index(inplace=True, drop=True)
    price = stock_quote.at[0, "Adj High"]
    return price


def quote_vix_open(date):
    # 查询underlying 市场行情
    query = f"SELECT * FROM `vix` where `date` = '{date}'"
    stock_quote = database.df_mysql_query(query)
    # 检查是否查询到合适的结果
    if stock_quote.empty:
        ex = Exception('stock_error')
        print(f'{date} quote_stock没有在vix中查询到符合的日期')
        raise ex
    stock_quote.reset_index(inplace=True, drop=True)
    price = stock_quote.at[0, "Open"]
    return price


# 获取今天以前的n天的last price(close price)平均值，为了数据口径一致，从option_table里面取underlying price
def moving_average(option_table_sql, n, date):
    # 用spx 的数据来获得交易日期
    # 查询underlying 市场行情
    query = f"SELECT * FROM `spx`"
    spx_data = database.df_mysql_query(query)
    spx_data.set_index('Date', drop=False, inplace=True)
    _end = spx_data.index.get_loc(date)
    _start = _end - n
    data_range = spx_data.iloc[_start:_end].copy() # 得到的交易日,用iloc不包括end这一天。注意，如果用loc就可以包括end这一天
    date_list = data_range['Date'].tolist()
    _ma = 0

    selected_data = database.df_mysql_query_from_list(option_table_sql, date_list)
    _ma = selected_data['Close'].mean()

    # for day in date_list:
    #     _ma += quote_stock(option_table_sql, day)
    # _ma = _ma/n
    return _ma


def get_full_data_from_sql_tock(stock_table_sql):
    # 查询underlying 市场行情
    query = f"SELECT * FROM {stock_table_sql}"
    stock_quote = database.df_mysql_query(query)
    #检查是否查询到合适的结果
    if stock_quote.empty:
        ex = Exception('stock_error')
        print(f'{date} quote_stock没有在{stock_table_sql} 中查询到符合的日期')
        raise ex
    stock_quote.reset_index(inplace=True, drop=True)
    return stock_quote


def compute_drawdown(net_values):
    """
    计算最大回撤
    :param net_values: 净值列表

    """
    # 最大回撤初始值设为0
    max_drawdown = 0
    index = 0
    # 双层循环找出最大回撤
    for net_value in net_values:
        # 计算从当前开始直到结束，和当前净值相比的最大回撤
        for sub_net_value in net_values[index:]:
            # 计算回撤
            # drawdown = -np.log(sub_net_value / net_value)
            drawdown = 1 - sub_net_value / net_value
            if drawdown > 100:
                print(index)
            # 如果当前的回撤大于已经计算的最大回撤，则当前回撤作为最大回撤
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        index += 1
    max_drawdown = round(max_drawdown * 100, 4)
    return max_drawdown


def compute_annual_profit(trading_days, final_net_value):
    """
    计算年化收益
    :param trading_days: 交易天数
    :param final_net_value: 期间总回报
    """
    annual_profit = 1
    annual_log_profit = 1
    # 交易日数大于0，才计算年化收益
    if trading_days > 0:
        # 计算年数
        years = trading_days / 250
        # 计算年化收益,转化为百分数
        total_log_return = np.log(final_net_value)
        annual_log_profit = total_log_return/years
        annual_profit = np.exp(annual_log_profit)-1
        # annual_profit = pow(final_net_value, 1 / years) - 1

    return annual_profit, annual_log_profit


def evaluation_netvalue_performance(net_values):
    """
    1.返回年化收益 2.年化夏普比 3.年化对数收益率，4.年化波动率，5.最大回撤
    :param net_values: 净值列表，必须从1开始的
    """
    # 总交易日数
    trading_days = len(net_values)
    # 所有收益的DataFrame
    profit_df = pd.DataFrame(columns={'profit'})
    # 计算每天的对数收益
    profit_df['profit'] = (np.log(net_values.astype(np.float64)) - np.log(net_values.astype(np.float64).shift(1)))

    # 初始化第一天的收益
    profit_df.iloc[0, 0] = 0

    # 计算收益
    daily_average_log_profit = profit_df['profit'].mean()
    annual_profit, annual_log_profit = compute_annual_profit(trading_days, net_values.iloc[-1])

    # 计算日收益标准差
    daily_std = profit_df['profit'].std()
    annual_std = daily_std * pow(250, 1 / 2)

    # 夏普比率
    annual_sharpe_ratio = annual_log_profit / annual_std

    # MMD
    MMD = compute_drawdown(net_values)

    # Sortino ratio
    profit_df['negative_profit'] = profit_df['profit']
    profit_df.loc[profit_df['negative_profit'] > 0, 'negative_profit'] = 0
    profit_df['negative_profit_squared'] = profit_df['negative_profit'].pow(2)
    downward_deviation = np.sqrt(profit_df['negative_profit_squared'].mean())
    annual_downward_deviation = downward_deviation * np.sqrt(250)
    sortino_ratio = daily_average_log_profit / downward_deviation
    annual_sortino_ratio = annual_log_profit/ annual_downward_deviation

    # return a tuple that contains 6 datas
    return (annual_profit*100).round(4), annual_sharpe_ratio.round(4), \
           annual_log_profit*100, annual_std*100, MMD, annual_sortino_ratio.round(4)


def generate_stock_netvalue(start_date, end_date, stock_symbol):

    query = f'SELECT * FROM `{stock_symbol}`'
    stock_quote = database.df_mysql_query(query)
    for day in [start_date, end_date]:
        if day in stock_quote['Date'].to_list():
            pass
        else:
            ex = Exception('stock_date_missing_error')
            print(f'{day} 没有在{stock_symbol}数据库中查询到符合的日期')
            raise ex
    stock_quote.set_index('Date', drop=False, inplace=True)
    netvalue = stock_quote.loc[start_date: end_date, 'Adj Close'] / stock_quote.loc[start_date, 'Adj Close']
    return netvalue




def export_plot(output_folder_path, title, width, height, data, plot_line_columns, plot_scatter_flags):
    date_column = pd.to_datetime(data['Date'], format='%Y-%m-%d')

    fig, ax = plt.subplots(figsize=(width, height))

    for column in plot_line_columns:
        ax.plot(date_column, data[column], label=column)

    scatter_marker_list = ['.', '*', 'x', 'v']
    marker_counter = 0
    for flag in plot_scatter_flags:
        ax.scatter(date_column, data[flag], label=flag, marker=scatter_marker_list[marker_counter])
        marker_counter += 1

    # 设置XY轴标签
    plt.xlabel('Date')
    plt.ylabel('Net Value (Log Scale)')

    # 设置log scale
    plt.yscale('log')

    # 设置X轴刻度
    # 设置X轴主要刻度
    major_locator = mdates.YearLocator(base=1, month=1, day=1)
    major_formatter = mdates.ConciseDateFormatter(major_locator)
    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_major_formatter(major_formatter)
    # 设置X轴次要刻度
    minor_locator = mdates.MonthLocator([4, 7, 10])
    minor_formatter = mdates.ConciseDateFormatter(minor_locator)
    ax.xaxis.set_minor_locator(minor_locator)
    ax.xaxis.set_minor_formatter(minor_formatter)

    # 设置Y轴刻度
    ax.yaxis.set_major_locator(tck.MaxNLocator(nbins='auto', prune='both'))
    ax.yaxis.set_major_formatter(tck.FormatStrFormatter("%.2f"))
    ax.yaxis.set_minor_formatter(tck.FormatStrFormatter("%.2f"))

    # 设置网格线
    ax.yaxis.grid(which='Major')
    ax.xaxis.grid(which='Major')

    # 设置图例
    plt.legend()

    # 设置图表标题
    plt.title(f'{title}')
    plt.savefig(f'{output_folder_path}\\{title}.jpg', dpi=300)
    plt.close()


def get_file_info(f_path):
    file_info = pd.DataFrame()

    all_files = glob.glob(f'{f_path}\\*.csv') # Return a possibly-empty list of path names that match pathname

    file_info['file_path'] = pd.Series(all_files)
    file_info.insert(loc=1, column='File', value='')
    file_info.insert(loc=2, column='DataDate', value='')
    file_info.insert(loc=3, column='File_no_extension', value='')

    n = len(file_info['file_path'])
    # 获取文件名，并放入File column
    for i in range(n):
        print(f'reading file info, this is the {i+1} file in {n} files')
        file_info.loc[i, 'File'] = os.path.basename(file_info.loc[i, 'file_path'])
        file_info.loc[i, 'File_no_extension'] = os.path.splitext(file_info.loc[i, 'File'])[0]

    # # 从文件名获取日期，并放入Date column
    # opt_info['DataDate'] = opt_info['File'].str.slice(stop=10)
    # opt_info['DataDate'] = pd.to_datetime(opt_info['DataDate'], format='%Y-%m-%d')
    # # opt_info.set_index('DataDate', drop=False, inplace=True)
    # opt_info.sort_values(by='DataDate', ascending=True, inplace=True)

    return file_info


if __name__ == '__main__':
    stock_type = check_symbol_and_type('a')
    print(stock_type)