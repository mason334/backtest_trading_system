from backtest_trading_system import trading_platform_stock_only as tp
from datetime import datetime
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
模拟对称vertical spread的效果，不考虑volatility skew带来的option cost。
根据upper limit, lower limit来构建模拟vertical spread.
百分比upper_limit = args[0]
百分比lower_limit = args[1]
rebalance_weekday = args[2]， 周一至周五，选择一天rebalance。Monday is 0 and Sunday is 6。
一般选择4，也就是周五来rebalance，因为周五期权到期。
rebalance_space = args[3]，rebalance的时间间隔，1就是每周rebalance，2就是每两周rebalance。

2020/8/16 zxc update
'''


class StrategyContext(tp.Context):
    def __init__(self):
        super().__init__()
        self.week_counter = 0  # 定义一个用来记录交易过去多少周的一个counter

    def handle_data(self, *args, **kwargs):
        upper_limit = round(args[0], 3)
        lower_limit = round(args[1], 3)
        rebalance_weekday = args[2]
        rebalance_space = args[3]

        # vix = tp.quote_vix_high(self.current_dt)

        if len(self.positions.SecuritySymbol.values) == 0:
            security = ''
        else:
            security = self.positions.SecuritySymbol.values[0]

        # 检查position为空，买股票
        if len(security) == 0:
            self.update_position_param()
            stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)
            amount = round(self.equity / stock_price) * self.leverage
            self.enter_stock_order(self.underlying_symbol, stock_price, amount)

        else:
            weekday = datetime.strptime(self.current_dt, '%Y-%m-%d').weekday()

            if weekday == rebalance_weekday:
                self.week_counter += 1
                if self.week_counter % rebalance_space == 0:
                    self.update_position_param()
                    # 按照当前价格区间，清仓
                    cost = self.positions.at[security, "CostBasis"]
                    stock_price = tp.quote_stock(self.underlying_symbol, self.current_dt)

                    price_change = stock_price/cost - 1

                    if price_change > upper_limit:
                        rebalance_price = cost * (1+upper_limit)
                    elif price_change < lower_limit:
                        rebalance_price = cost * (1+lower_limit)
                    else:
                        rebalance_price = stock_price

                    amount = -self.positions.at[security, "Amount"]
                    self.enter_stock_order(self.underlying_symbol, rebalance_price, amount)

                    # 按照市场价，重新建仓
                    self.update_position_param()
                    amount = round(self.equity / stock_price) * self.leverage
                    self.enter_stock_order(self.underlying_symbol, stock_price, amount)

                    self.rebalance_flag = 1





