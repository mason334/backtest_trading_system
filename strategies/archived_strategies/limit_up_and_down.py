from backtest_trading_system import trading_platform_stock_only as tp
import pandas as pd
import traceback
from playsound import playsound
import math

'''
策略简介
模拟对称vertical spread的效果，不考虑volatility skew带来的option cost。
rebalance_span = args[0] 选择多少天rebalance，也就是指expire的时间。
upper_limit = args[1]
lower_limit = args[2]

由于rebalace span是可以随意选择的，所以这个策略不实际。
因为真正的vertical spread只能在周五expire。

2020/8/16 zxc update

'''


class StrategyContext(tp.Context):
    def handle_data(self, *args, **kwargs):

        rebalance_span = args[0]
        upper_limit = args[1]
        lower_limit = args[2]

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
            if self.elapsed_trade_days % rebalance_span == 0:
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





