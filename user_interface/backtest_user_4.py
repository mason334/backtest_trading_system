from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scan_parameters = pd.read_csv('E:\\Strategy_output\\vix_macd_defensive_buy_dip\\Scan_parameters\\'
                                  'vix_scan_4.csv')

    output_folder = 'E:\\Strategy_output\\vix_macd_defensive_buy_dip\\soxl_201807_202009_no_buy_dip'

    init_settings = {
        'start_date': '2018-07-30',
        'end_date': '2020-09-04',

        'underlying_symbol': 'soxl',
        'underlying_symbol_2': '',

        'option_table': 'soxl_option',
        'option_table_2': '',

        'benchmark': ['soxl'],

        'leverage': 1,
        'stock_maintenance_margin': 0.5,
        'option_maintenance_margin': 0.05,
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag',
                               # 'StockPositionFlag',
                               # 'OptSubstitutionFlag',
                               # 'DefendStatus',
                               # 'BuyDipStatus'
                               # 'ContractDisappearFlag'
                               ],
        'earnings_date_list': []
    }

    strategy_name = 'backtest_trading_system.strategies.vix_macd_defensive_buy_dip'

    backtest_engine.backtest(strategy_name, scan_parameters, output_folder, init_settings)