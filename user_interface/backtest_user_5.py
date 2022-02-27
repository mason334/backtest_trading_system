from backtest_trading_system import backtest_engine
import pandas as pd

if __name__ == '__main__':

    scan_parameters = pd.read_csv('E:\\Strategy_output\\macd_defense_macd_buy_dip\\scan_parameters\\'
                            'vix_scan_3.csv')

    output_folder = 'E:\\Strategy_output\\macd_defense_macd_buy_dip\\QQQ_GLD_200701_202005'

    init_settings = {
        'start_date': '2007-01-03',
        'end_date': '2020-05-06',

        'underlying_symbol': 'qqq',
        'underlying_symbol_2': 'gld',

        'option_table': 'qqq_option',
        'option_table_2': '',

        'benchmark': ['qqq', 'vix', 'gld'],

        'leverage': 1,
        'stock_maintenance_margin': 0.1,
        'option_maintenance_margin': 0.05,
        'target_delta': 5,
        'plot_scatter_flags': ['RebalanceFlag',
                               # 'StockPositionFlag',
                               # 'OptSubstitutionFlag',
                               # 'ContractDisappearFlag'
                               'DefendStatus',
                               'BuyDipStatus'
                               ],
        'earnings_date_list': []
    }

    strategy_name = 'backtest_trading_system.strategies.macd_defense_macd_buy_dip'

    backtest_engine.backtest(strategy_name, scan_parameters, output_folder, init_settings)