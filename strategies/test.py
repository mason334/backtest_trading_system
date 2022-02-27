import pandas as pd
import numpy as np
from backtest_trading_system import trading_tools as tools
from statsmodels.stats.descriptivestats import describe
from scipy import stats

d = {
    'Name':['Alisa','Bobby','Cathrine','Madonna','Rocky','Sebastian','Jaqluine',
   'Rahul','David','Andrew','Ajay','Teresa'],
   'Score1':[62,47,55,74,31,77,85,85.1,42,32,71,57],
   'Score2':[89,87,67,55,47,72,76,79,44,92,99,69],
   'Score3':[56,86,77,45,73,62,74,89,71,67,97,68]}

df = pd.DataFrame(d)

df['Score1'] = df['Score1']/33.56
score_1_descipt = describe(d['Score1'])
print(score_1_descipt)

# rng = np.random.default_rng()
rvs1 = stats.norm.rvs(loc=4, scale=10, size=1500)
rvs2 = stats.norm.rvs(loc=44, scale=10, size=150)
a, b = stats.ttest_ind(rvs1, rvs2, equal_var=False)

# net_values = df['Score1']
#
# df['logreturn'] = (np.log(net_values) - np.log(net_values.shift(1)))*100
# df['logreturn'] = df['logreturn'].round(2)
# df.loc[0, 'logreturn'] = round(np.log(net_values[0]) * 100, 2)
#
# print(df)
# print(df['logreturn'].std().round(2))
# lockon = tools.quote_option_market('nvda_option', 'call', '60', '0', '2015-01-04')
# print(lockon)

stock = tools.quote_stock('nvda', '2015-01-02')
print(stock)

option = tools.quote_option_symbol('nvda_option', 'NVDA150220P15', '2015-01-04')
print(option)