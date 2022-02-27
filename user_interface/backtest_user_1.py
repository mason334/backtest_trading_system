from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scan_parameters = pd.read_csv('E:\\Strategy_output\\martingale\\'
                                  'vix_scan_1_martingale_nonlinear.csv')

    output_folder = 'E:\\Strategy_output\\martingale\\spy_201101_202009_martingale_nonlinear'

    init_settings = {
        'start_date': '2011-01-05',
        'end_date': '2020-09-30',

        'underlying_symbol': 'spy',
        'underlying_symbol_2': 'spy',

        'option_table': '',
        'option_table_2': '',

        'benchmark': ['spy'],

        'leverage': 1,
        'stock_maintenance_margin': 0.01,
        'option_maintenance_margin': 0.01,
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag',
                               # 'StockPositionFlag',
                               # 'OptSubstitutionFlag',
                               # 'ContractDisappearFlag'
                               # 'DefendStatus',
                               # 'BuyDipStatus'
                               ],
        'earnings_date_list': []

    }

    strategy_name = 'backtest_trading_system.strategies.martingale'

    backtest_engine.backtest(strategy_name, scan_parameters, output_folder, init_settings)