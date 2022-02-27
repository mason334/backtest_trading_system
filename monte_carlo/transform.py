import pandas as pd

original_data = pd.read_csv('E:\\Strategy_output\\bull_card_simulation\\2022-2-11\\cash_record_100000.csv')
print(original_data.head())
transformed_data = original_data.T
print(transformed_data.head)
transformed_data.to_csv('E:\\Strategy_output\\bull_card_simulation\\2022-2-11\\cash_record_100000_transformed.csv')