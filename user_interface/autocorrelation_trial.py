df = pd.read_csv('I:\\投资理财\\股票\\return 聚集效应\\qqq_lag_data_2018_202103.csv')
lag_data = pd.read_csv('I:\\投资理财\\股票\\return 聚集效应\\qqq_lag_data_2018_202103.csv')


# stock_return = df['Ln_return']
abs_stock_return = df['abs_ln_return']



# print(stock_return)

# Calculate ACF and PACF upto 20 lags
acf_stock, acf_stock_confint = acf(abs_stock_return, nlags=20, alpha=0.05)
pacf_stock, pacf_stock_confint = pacf(abs_stock_return, nlags=20, alpha=0.05)
print(f'acf_stock{acf_stock}, ')
print(f'acf_stock_confint {acf_stock_confint}, ')
print(f'pacf_stock {pacf_stock}, ')
print(f'pacf_stock_confint{pacf_stock_confint}')


# print(f'acf_temperatures{acf_temperatures}')
# print(f'acf_temperatures_confint{acf_temperatures_confint}')
# print(f'pacf_temperatures{pacf_temperatures}')
# print(f'pacf_temperatures_confint{pacf_temperatures_confint}')



# Draw Plot

plot_acf(abs_stock_return, lags=50)
plot_pacf(abs_stock_return, lags=50)

output_folder_path = 'E:\\Strategy_output\\autocorrelation_analysis'
plt.savefig(f'{output_folder_path}\\pacf_stock.jpg', dpi=300)

plt.show()

Y = lag_data['abs_ln_return']

X10 = lag_data[['AR1', 'AR2', 'AR3', 'AR4', 'AR5', 'AR6','AR7', 'AR8', 'AR9', 'AR10']]
X10_C = sm.add_constant(X10)  # adding a constant
ar10_model = sm.OLS(Y, X10_C).fit()
ar10_model_summary = ar10_model.summary()
print(ar10_model_summary)

X5 = lag_data[['AR1', 'AR2', 'AR3', 'AR4', 'AR5']]
X5_C = sm.add_constant(X5)  # adding a constant
ar5_model = sm.OLS(Y, X5_C).fit()
ar5_model_summary = ar5_model.summary()
print(ar5_model_summary)


X3 = lag_data[['AR1', 'AR2', 'AR3']]
X3_C = sm.add_constant(X3)  # adding a constant
ar3_model = sm.OLS(Y, X3_C).fit()
ar3_model_summary = ar3_model.summary()
print(ar3_model_summary)


X1 = lag_data['AR1']
X1_C = sm.add_constant(X1)  # adding a constant
ar1_model = sm.OLS(Y, X1_C).fit()
ar1_model_summary = ar1_model.summary()
print(ar1_model_summary)