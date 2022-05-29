import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import datetime

data_dir = 'C:/Users/Sachin M/PycharmProjects/IB_Projects/Straddle/data/'

tradelog_df = pd.read_csv(data_dir+'Tradelog_920.csv', index_col=[0], parse_dates=True)

def backtest_metrics(tradelog_df, capital, quantity):
    try:
        tradelog_df['Entry_Datetime'] = tradelog_df['Entry_Datetime'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S'))
        tradelog_df['Date'] = tradelog_df['Entry_Datetime'].apply(lambda x: x.date())

        initial_capital = capital
        tradelog_df['Quantity'] = quantity
        # tradelog_df['Total_PnL'] = tradelog_df['PnL'] * 25

        tradelog_df['Entry_Price'] = tradelog_df['CE_Entry_Price'] + tradelog_df['PE_Entry_Price']
        tradelog_df['Exit_Price'] = tradelog_df['CE_Exit_Price'] + tradelog_df['PE_Exit_Price']
        tradelog_df['PnL_wout_slippage'] = (tradelog_df['Entry_Price'] - tradelog_df['Exit_Price']) * 25

        tradelog_df['Entry_Price_Slippage'] = tradelog_df['Entry_Price'] - (tradelog_df['Entry_Price'] * 0.01)
        tradelog_df['Exit_Price_Slippage'] = tradelog_df['Exit_Price'] + (tradelog_df['Exit_Price'] * 0.01)
        tradelog_df['PnL_Slippage'] = (tradelog_df['Entry_Price_Slippage'] - tradelog_df['Exit_Price_Slippage']) * 25

        tradelog_df['Pnl_Slippage_Cumsum'] = tradelog_df['PnL_Slippage'].cumsum()

        tradelog_df['Equity'] = 0
        tradelog_df['Rate_of_return'] = 0

        for i in range(len(tradelog_df)):
            if i == 0:
                tradelog_df['Equity'].iloc[i] = initial_capital + tradelog_df['PnL_Slippage'].iloc[i]
                tradelog_df['Rate_of_return'].iloc[i] = (tradelog_df['PnL_Slippage'].iloc[i] / initial_capital) * 100
            else:
                tradelog_df['Equity'].iloc[i] = tradelog_df['Equity'].iloc[i - 1] + tradelog_df['PnL_Slippage'].iloc[i]
                tradelog_df['Rate_of_return'].iloc[i] = (tradelog_df['PnL_Slippage'].iloc[i] / initial_capital) * 100

        ## Win Rate
        win_rate = round(len(tradelog_df[tradelog_df['PnL_Slippage'] > 0]) / len(tradelog_df) * 100, 2)

        ## Mean Win
        mean_win = round(tradelog_df[tradelog_df['PnL_Slippage'] > 0]['PnL_Slippage'].mean(), 2)

        ## Mean Loss
        mean_loss = round(tradelog_df[tradelog_df['PnL_Slippage'] < 0]['PnL_Slippage'].mean(), 2)

        # risk_reward
        risk_reward = abs(mean_win / mean_loss)

        ##Sharpe Ratio
        trading_days_a_year = 252
        risk_free_interest = 5
        mean = tradelog_df['Rate_of_return'].mean() * trading_days_a_year - risk_free_interest
        volatility = tradelog_df['Rate_of_return'].std() * np.sqrt(trading_days_a_year)
        sharpe_ratio = round(mean / volatility, 2)

        ##Sortino Ratio
        negative_std_deviation = tradelog_df[tradelog_df['Rate_of_return'] < 0]['Rate_of_return'].std() * np.sqrt(
            trading_days_a_year)
        sortino_ratio = round(mean / negative_std_deviation, 2)

        ##Max Drawdown
        tradelog_df['Drawdown'] = tradelog_df['Pnl_Slippage_Cumsum'] - tradelog_df['Pnl_Slippage_Cumsum'].cummax()
        max_drawdown = round(tradelog_df['Drawdown'].min(), 2)

        ##Max Drawdown Percent
        max_drawdown_percent = round(
            max_drawdown / tradelog_df[tradelog_df['Drawdown'] == tradelog_df['Drawdown'].min()]['Equity'].iloc[0] * 100, 2)

        ##Recovery Trade
        tradelog_df['Recovery_Trades'] = 0
        for i in range(len(tradelog_df)):
            if (tradelog_df['Drawdown'].iloc[i] < 0):
                tradelog_df['Recovery_Trades'].iloc[i] = tradelog_df['Recovery_Trades'].iloc[i - 1] + 1
        recovery_trades = tradelog_df['Recovery_Trades'].max()

        ##Recovery Days
        trade_log_equity_high = tradelog_df[tradelog_df['Recovery_Trades'] == 0]
        trade_log_equity_high['number_days_between_equity_highs'] = (trade_log_equity_high['Entry_Datetime'] -
                                                                     trade_log_equity_high['Entry_Datetime'].shift())
        recovery_days = int(trade_log_equity_high['number_days_between_equity_highs'].apply(lambda x: x.days).max())

        ##Cagr
        backtest_days = (tradelog_df.iloc[-1]['Entry_Datetime'].date() - tradelog_df.iloc[0]['Entry_Datetime'].date()).days
        cagr = (((tradelog_df.iloc[-1]['Equity'] / initial_capital) ** (1 / (backtest_days / 365))) - 1) * 100

        ##Calmar
        calmar_ratio = round(abs(cagr / max_drawdown_percent), 2)

        start_date = tradelog_df.iloc[0]['Entry_Datetime'].date()
        end_date = tradelog_df.iloc[-1]['Entry_Datetime'].date()
        number_of_trades = len(tradelog_df)

        ##number of wins
        number_of_wins = len(tradelog_df[tradelog_df['PnL_Slippage'] > 0])

        ##number of losses
        number_of_losses = len(tradelog_df[tradelog_df['PnL_Slippage'] < 0])

        ## average profit per trade
        average_profit_per_trade = round(tradelog_df[tradelog_df['PnL_Slippage'] > 0]['PnL_Slippage'].mean(), 2)

        ## average loss per trade
        average_loss_per_trade = round(tradelog_df[tradelog_df['PnL_Slippage'] < 0]['PnL_Slippage'].mean(), 2)

        ##max pnl
        max_pnl = round(tradelog_df['PnL_Slippage'].max(), 2)

        ##min_pnl
        min_pnl = round(tradelog_df['PnL_Slippage'].min(), 2)

        ##median_of_trade
        median_of_trade = round(tradelog_df['PnL_Slippage'].median(), 2)

        ##Profit factor
        gross_profit = tradelog_df[tradelog_df['PnL_Slippage'] > 0]['PnL_Slippage'].sum()
        gross_loss = tradelog_df[tradelog_df['PnL_Slippage'] < 0]['PnL_Slippage'].sum()
        profit_factor = round(abs(gross_profit / gross_loss), 2)


        ##Consecutive wins and consecutive losses
        tradelog_df['Continuous_Wins'] = 0
        tradelog_df['Continuous_Losses'] = 0

        for i in range(1, len(tradelog_df)):
            if tradelog_df['PnL_Slippage'].iloc[i - 1] > 0:
                tradelog_df['Continuous_Wins'].iloc[i] = tradelog_df['Continuous_Wins'].iloc[i - 1] + 1
            if tradelog_df['PnL_Slippage'].iloc[i - 1] < 0:
                tradelog_df['Continuous_Losses'].iloc[i] = tradelog_df['Continuous_Losses'].iloc[i - 1] + 1

        consecutive_wins = tradelog_df['Continuous_Wins'].max()
        consecutive_losses = tradelog_df['Continuous_Losses'].max()

        #Creating backtest matrics dataframe
        backtest_metrics = pd.DataFrame(
            columns=['Backtest Start Date', 'Backtest End Date', 'Number of Trades', 'Number of Wins',
                     'Number of Losses', 'Average Profit', 'Average Loss', 'Maximum Profit Points',
                     'Maximum Loss Points', 'Median Trade', 'Win Rate', 'Sharpe Ratio',
                     'Sortino Ratio', 'Max Drawdown', 'Max Drawdown Percent',
                     'Days Taken to Recover From Drawdown', 'Number of Trades to Recover From Drawdown',
                     'Calmar', 'CAGR', 'Consecutive Wins', 'Consecutive Losses',
                     'Profit Factor (Amount of Profit per unit of Loss)',
                     ])

        backtest_metrics = backtest_metrics.append({'Backtest Start Date': start_date,
                                                    'Backtest End Date': end_date,
                                                    'Number of Trades': number_of_trades,
                                                    'Number of Wins': number_of_wins,
                                                    'Number of Losses': number_of_losses,
                                                    'Average Profit': average_profit_per_trade,
                                                    'Average Loss': average_loss_per_trade,
                                                    'Maximum Profit Points': max_pnl,
                                                    'Maximum Loss Points': min_pnl,
                                                    'Median Trade': median_of_trade,
                                                    'Win Rate': win_rate,
                                                    'Sharpe Ratio': sharpe_ratio,
                                                    'Sortino Ratio': sortino_ratio,
                                                    'Max Drawdown': max_drawdown,
                                                    'Max Drawdown Percent': max_drawdown_percent,
                                                    'Days Taken to Recover From Drawdown': recovery_days,
                                                    'Number of Trades to Recover From Drawdown': recovery_trades,
                                                    'Calmar': calmar_ratio,
                                                    'CAGR': cagr,
                                                    'Consecutive Wins': consecutive_wins,
                                                    'Consecutive Losses': consecutive_losses,
                                                    'Profit Factor (Amount of Profit per unit of Loss)': profit_factor,
                                                    },
                                                   ignore_index=True)
        return backtest_metrics.T
    except Exception as Ex:
        print(Ex)

backtest_result = backtest_metrics(tradelog_df, 150000, 25)
print(backtest_result)