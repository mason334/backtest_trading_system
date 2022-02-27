from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scan_parameters = pd.read_csv('E:\\Strategy_output\\vix_long_short_hedging\\'
                                  'long_short_all_condition_vix.csv')

    output_folder = 'E:\\Strategy_output\\vix_long_short_hedging\\qqq_xlp_200808_201009'

    init_settings = {
        'start_date': '2008-08-21',
        'end_date': '2010-09-01',

        'underlying_symbol': 'qqq',
        'underlying_symbol_2': 'xlp',

        'option_table': 'nvda_option',
        'option_table_2': '',

        'benchmark': ['qqq', 'xlp'],

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

    strategy_name = 'backtest_trading_system.strategies.vix_long_short_hedging'

    backtest_engine.backtest(strategy_name, scan_parameters, output_folder, init_settings)