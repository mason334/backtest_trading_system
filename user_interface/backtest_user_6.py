from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scenarios = pd.read_csv('E:\\Strategy_output\\MACD\\'
                            'scan.csv')

    output_folder = 'E:\\Strategy_output\\MACD\\GLD_2015_2016'

    init_settings = {
        'start_date': '2015-01-02',
        'end_date': '2016-05-20',

        'underlying_symbol': 'gld',
        'underlying_symbol_2': '',

        'option_table': 'gld_option',
        'option_table_2': '',

        'benchmark': ['gld'],

        'leverage': 1,
        'stock_maintenance_margin': 0.1,
        'option_maintenance_margin': 0.05,
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag',
                               # 'StockPositionFlag',
                               # 'OptSubstitutionFlag',
                               'ContractDisappearFlag'],
        'earnings_date_list': []
    }

    strategy_name = 'backtest_trading_system.strategies.macd'

    backtest_engine.backtest(strategy_name, scenarios, output_folder, init_settings)