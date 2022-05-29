import pandas as pd
import os
import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil.relativedelta import relativedelta, TH
import numpy as np

#Reading banknifty futures data to extract trading days
stock_dir = 'C:/Users/Sachin M/PycharmProjects/IB_Projects/Straddle/data'
os.chdir(stock_dir)
df = pd.read_csv('BANKNIFTY_Combined.csv')
df['date'] = pd.to_datetime(df['date'])
df['Date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
df['Date'] = df['date'].dt.strftime('%Y-%m-%d')

#Trading dates
fut_dates = pd.to_datetime(df['Date'].unique()).tolist()

#Options strikes ohlcv data directory
options_dir = 'C:/Users/Sachin M/PycharmProjects/IB_Projects/Straddle/options_data'
os.chdir(options_dir)

#Creating dataframe to store tradelogs
Intraday_trade_log = pd.DataFrame(columns=['Entry_Datetime',
                                               'ATM_Strike', 'Days_to_Expiry',
                                               'CE_Symbol', 'CE_Entry_Price',
                                               'CE_Exit_Price', 'CE_Exit_Datetime',
                                               'PE_Symbol', 'PE_Entry_Price',
                                               'PE_Exit_Price',
                                               'PE_Exit_Datetime', 'PnL'])

#Creating tradelogs
for i in range(len(fut_dates)):
    try:
        print(fut_dates[i])

        nearest_expiry = fut_dates[i].date() + relativedelta(weekday=TH(+1))

        entry_datetime = datetime.datetime.combine(fut_dates[i].date(), datetime.time(9, 20))
        exit_datetime = datetime.datetime.combine(fut_dates[i].date(), datetime.time(14, 30))

        base = 100
        atm = df[df['date'] == entry_datetime]['open'].iloc[0]
        atm = base * round(atm / base)

        opt_dir_ce = "BANKNIFTY_{nearest_expiry}_OPT_{atm}.0_CE.csv".format(nearest_expiry=nearest_expiry, atm=atm)
        opt_dir_pe = "BANKNIFTY_{nearest_expiry}_OPT_{atm}.0_PE.csv".format(nearest_expiry=nearest_expiry, atm=atm)

        opt_ce_df = pd.read_csv(opt_dir_ce)
        opt_ce_df.rename(columns={'Unnamed: 0': 'date'}, inplace=True)
        opt_ce_df['date'] = pd.to_datetime(opt_ce_df['date'])
        opt_ce_df['date'] = pd.to_datetime(opt_ce_df['date'], format="%Y-%m-%d %H:%M:%S")
        opt_ce_df.set_index(opt_ce_df['date'], inplace=True)

        entry_time_index = opt_ce_df[opt_ce_df['date'] == entry_datetime].index[0]
        exit_time_index = opt_ce_df[opt_ce_df['date'] == exit_datetime].index[0]
        opt_ce_df_fil = opt_ce_df[entry_time_index:exit_time_index]

        opt_pe_df = pd.read_csv(opt_dir_pe)
        opt_pe_df.rename(columns={'Unnamed: 0': 'date'}, inplace=True)
        opt_pe_df['date'] = pd.to_datetime(opt_pe_df['date'])
        opt_pe_df['date'] = pd.to_datetime(opt_pe_df['date'], format="%Y-%m-%d %H:%M:%S")
        opt_pe_df.set_index(opt_pe_df['date'], inplace=True)

        opt_pe_df_fil = opt_pe_df[entry_time_index:exit_time_index]

        ce_data = opt_ce_df_fil[['date', 'close']].set_index('date')
        pe_data = opt_pe_df_fil[['date', 'close']].set_index('date')

        intraday_data = pd.concat([ce_data, pe_data], axis=1)
        intraday_data.columns = ['ce_close', 'pe_close']
        intraday_data.reset_index(inplace=True)

        ce_symbol = "{symbol}_CE".format(symbol=atm)
        pe_symbol = "{symbol}_PE".format(symbol=atm)

        strike = atm

        ce_entry_price = intraday_data[intraday_data['date'] == entry_datetime]['ce_close'].iloc[0]
        pe_entry_price = intraday_data[intraday_data['date'] == entry_datetime]['pe_close'].iloc[0]

        ce_stoploss_price = 0
        pe_stoploss_price = 0

        ce_exit_price = 0
        pe_exit_price = 0

        ce_exit_datetime = ''
        pe_exit_datetime = ''

        stoploss_percent = 30 / 100
        ce_stop_loss = ce_entry_price + stoploss_percent * ce_entry_price
        pe_stop_loss = pe_entry_price + stoploss_percent * pe_entry_price

        ce_pnl = 0
        pe_pnl = 0
        pnl = 0

        ce_sl_flag = 0
        pe_sl_flag = 0

        for index, row in intraday_data.iterrows():
            ce_ltp = row['ce_close']
            pe_ltp = row['pe_close']

            # CE and PE stoploss were not hit and time = 15:00pm
            if (ce_sl_flag == 0) & (pe_sl_flag == 0) & (row['date'] == exit_datetime):
                ce_sl_flag = 1
                pe_sl_flag = 1

                ce_pnl = ce_entry_price - ce_ltp
                pe_pnl = pe_entry_price - pe_ltp

                pnl = ce_pnl + pe_pnl

                ce_exit_price = ce_ltp
                pe_exit_price = pe_ltp

                ce_exit_datetime = row['date']
                pe_exit_datetime = row['date']

                print('CE and PE Stop loss not hit and exited on 15:00pm')

                break
            # CE stop loss hit
            elif (ce_ltp >= ce_stop_loss) & (ce_sl_flag == 0) & (pe_sl_flag == 0):
                ce_sl_flag = 1

                ce_pnl = ce_entry_price - ce_ltp
                pe_pnl = pe_entry_price - pe_ltp

                pnl = ce_pnl + pe_pnl

                ce_exit_price = ce_ltp

                ce_exit_datetime = row['date']

                print('CE stoploss hit')

            # pe stop loss hit
            elif (pe_ltp >= pe_stop_loss) & (ce_sl_flag == 0) & (pe_sl_flag == 0):
                pe_sl_flag = 1

                ce_pnl = ce_entry_price - ce_ltp
                pe_pnl = pe_entry_price - pe_ltp

                pnl = ce_pnl + pe_pnl

                pe_exit_price = pe_ltp

                pe_exit_datetime = row['date']

                print('PE stoploss hit')

            # ce stop loss hit already and pe stop loss hit
            elif (ce_sl_flag == 1) & (pe_sl_flag == 0):
                if (pe_ltp >= pe_stop_loss) & (row['date'] < exit_datetime):
                    pe_sl_flag = 1

                    pe_pnl = pe_entry_price - pe_ltp

                    pnl = ce_pnl + pe_pnl

                    pe_exit_price = pe_ltp

                    pe_exit_datetime = row['date']

                    print("CE stop loss was hit and now PE stop loss hit")

                    break
                # ce stop loss was hit and pe exited at 15:00pm
                elif row['date'] == exit_datetime:
                    pe_sl_flag = 1

                    pe_pnl = pe_entry_price - pe_ltp

                    pnl = ce_pnl + pe_pnl

                    pe_exit_price = pe_ltp

                    pe_exit_datetime = row['date']

                    print("CE stop loss was hit and PE exited on 15:00pm")

                    break

            # pe stop loss hit already and ce stop loss hit
            elif (ce_sl_flag == 0) & (pe_sl_flag == 1):
                if (ce_ltp >= ce_stop_loss) & (row['date'] < exit_datetime):
                    ce_sl_flag = 1

                    ce_pnl = ce_entry_price - ce_ltp

                    pnl = ce_pnl + pe_pnl

                    ce_exit_price = ce_ltp

                    ce_exit_datetime = row['date']

                    print("PE stop loss was hit and now CE stop loss hit")

                    break

                elif (row['date'] == exit_datetime):

                    ce_sl_flag = 1

                    ce_pnl = ce_entry_price - ce_ltp

                    pnl = ce_pnl + pe_pnl

                    ce_exit_price = ce_ltp

                    ce_exit_datetime = row['date']

                    print("PE stop loss was hit and CE exited on 15:00pm")

                    break

        Intraday_trade_log = Intraday_trade_log.append({"Entry_Datetime": entry_datetime,
                                                        "ATM_Strike": atm,
                                                        "Days_to_Expiry": (nearest_expiry - entry_datetime.date()).days,
                                                        "CE_Symbol": ce_symbol,
                                                        "CE_Entry_Price": ce_entry_price,
                                                        "CE_Exit_Price": ce_exit_price,
                                                        "CE_Exit_Datetime": ce_exit_datetime,
                                                        "PE_Symbol": pe_symbol,
                                                        "PE_Entry_Price": pe_entry_price,
                                                        "PE_Exit_Price": pe_exit_price,
                                                        "PE_Exit_Datetime": pe_exit_datetime,
                                                        "PnL": pnl}, ignore_index=True)

    except Exception as Ex:
        print(Ex)
        print(fut_dates[i])

pd.set_option('display.max_rows',400)
pd.set_option('display.max_columns',400)

stock_dir = 'C:/Users/Sachin M/PycharmProjects/IB_Projects/Straddle/data'
os.chdir(stock_dir)

print(Intraday_trade_log)
Intraday_trade_log.to_csv("Tradelog_920.csv")