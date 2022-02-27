from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scan_parameters = pd.read_csv('E:\\Strategy_output\\limit_up_and_down_weekday\\'
                                  'parameter_fine_asymmetric_weekday.csv')

    output_folder = 'E:\\Strategy_output\\limit_up_and_down_weekday\\spy_200801_201009_fine_weekly_asymmetric'

    init_settings = {
        'start_date': '2008-01-10',
        'end_date': '2010-05-20',

        'underlying_symbol': 'spy',
        'underlying_symbol_2': '',

        'option_table': 'spy_option',
        'option_table_2': '',

        'benchmark': ['spy'],

        'leverage': 1,
        'stock_maintenance_margin': 0.5,
        'option_maintenance_margin': 0.05,
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

    strategy_name = 'backtest_trading_system.strategies.limit_up_and_down_weekday'

    backtest_engine.backtest(strategy_name, scan_parameters, output_folder, init_settings)