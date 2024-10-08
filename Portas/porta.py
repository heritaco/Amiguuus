import pandas as pd  # For data manipulation and analysis
import numpy as np  # For numerical operations
import requests  # For making HTTP requests to fetch data from web pages
import os  # For interacting with the operating system (e.g., file paths)
import yfinance as yf  # For fetching financial data from Yahoo Finance

# PyPortfolioOpt library for portfolio optimization
from pypfopt.efficient_frontier import EfficientFrontier  # For creating efficient frontier and optimizing portfolios
from pypfopt import risk_models  # For calculating risk models (e.g., covariance matrix)
from pypfopt import expected_returns  # For calculating expected returns

# PyPortfolioOpt library for discrete allocation
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices  # For discrete allocation of portfolio weights

import requests  # Duplicate import, already imported above
from bs4 import BeautifulSoup  # For parsing HTML and XML documents
import pandas as pd  # Duplicate import, already imported above

from datetime import datetime  # For manipulating dates and times

from forex_python.converter import CurrencyRates
import pandas as pd
from pypfopt import expected_returns, risk_models

import pandas as pd  # For data manipulation and analysis
import numpy as np  # For numerical operations
import requests  # For making HTTP requests to fetch data from web pages
import os  # For interacting with the operating system (e.g., file paths)
import yfinance as yf  # For fetching financial data from Yahoo Finance

# PyPortfolioOpt library for portfolio optimization
from pypfopt.efficient_frontier import EfficientFrontier  # For creating efficient frontier and optimizing portfolios
from pypfopt import risk_models  # For calculating risk models (e.g., covariance matrix)
from pypfopt import expected_returns  # For calculating expected returns

# PyPortfolioOpt library for discrete allocation
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices  # For discrete allocation of portfolio weights

from datetime import datetime  # For manipulating dates and times
from openpyxl import load_workbook  # For saving to Excel

def get_df():
    
    def read_stock_symbols(file_path):
        with open(file_path, 'r') as file:
            return file.read().splitlines()

    def fetch_adj_close_prices(symbols):
        adj_close_list = []
        for symbol in symbols:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="max")
            hist.reset_index(inplace=True)
            hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None) 
            daily_data = hist.groupby(hist['Date'].dt.date).agg({'Close': 'last'}).rename(columns={'Close': symbol})
            adj_close_list.append(daily_data)
        return pd.concat(adj_close_list, axis=1)

    def generate_all_dates(start_date, end_date):
        return pd.date_range(start=start_date, end=end_date, freq='D')

    current_date = datetime.now().strftime("%Y-%m-%d")
    csv_file = f"{current_date}.csv"

    if not os.path.exists(csv_file):
        stock_symbols = read_stock_symbols('ETFS&Stocks.txt')
        stock_symbols.insert(0, '^GSPC')
        
        df = fetch_adj_close_prices(stock_symbols)

        min_date = df.index.min()
        max_date = df.index.max()

        all_dates = pd.DataFrame(generate_all_dates(min_date, max_date), columns=['Date'])

        all_dates['Date'] = pd.to_datetime(all_dates['Date'])
        df.reset_index(inplace=True)
        df['Date'] = pd.to_datetime(df['Date']) 
        merged_df = all_dates.merge(df, on='Date', how='left')
        merged_df.set_index('Date', inplace=True)
        merged_df.to_csv(csv_file, index=True)

    df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
    return df

def remove_etfs(df):
    # Ensure df is not None
    if df is None:
        raise ValueError("The DataFrame 'df' is None. Please provide a valid DataFrame.")

    # Read the column names from ETFS.txt
    try:
        with open('ETFS.txt', 'r') as file:
            columns_to_drop = [line.strip() for line in file]

        # Check if columns to drop exist in the DataFrame
        missing_columns = [col for col in columns_to_drop if col not in df.columns]
        if missing_columns:
            raise ValueError(f"The following columns are not found in the DataFrame: {missing_columns}")

        # Drop the columns from the DataFrame
        df.drop(columns=columns_to_drop, inplace=True)
        print("Columns dropped successfully.")
    except FileNotFoundError:
        print("The file 'ETFS.txt' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")


def portapara(df, portafolio, days, rf):

    mxntodlls = .05
    portafolio = portafolio * mxntodlls

    rf = (1 + rf) ** (252 / days) - 1

    current_date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    mu = expected_returns.mean_historical_return(df, frequency=days)
    s = risk_models.sample_cov(df, frequency=days)

    def save_to_excel(file_path, expected_return, volatility, sharpe_ratio, rf, leftover, type):
        workbook = load_workbook(file_path)
        sheet = workbook.active

        sheet["E1"] = type
        sheet["E2"] = "Days"
        sheet["E3"] = "Portafolio value"
        sheet["E4"] = "Return"
        sheet["E5"] = "Volatility"
        sheet["E6"] = "Sharpe Ratio"
        sheet["E7"] = "Risk-Free Rate"
        sheet["E8"] = "Leftover"
        sheet["F2"] = days
        sheet["F3"] = portafolio
        sheet["F4"] = expected_return
        sheet["F5"] = volatility
        sheet["F6"] = sharpe_ratio
        sheet["F7"] = rf
        sheet["F8"] = leftover

        workbook.save(file_path)

    class PortfolioOptimization:
        def __init__(self, mu, s, portafolio, rf):
            self.mu = mu
            self.s = s
            self.portafolio = portafolio
            self.rf = rf

        def max_sharpe(self):
            
            ef = EfficientFrontier(self.mu, self.s)

            weights = ef.max_sharpe(risk_free_rate=self.rf)
            cleaned_weights = ef.clean_weights()

            performance = ef.portfolio_performance(verbose=True, risk_free_rate=self.rf)
            expected_return, volatility, sharpe_ratio = performance

            latest_prices = get_latest_prices(df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.portafolio)
            allocation, leftover = da.lp_portfolio()

            discrete_allocation_list = [allocation[symbol] for symbol in allocation]

            portfolio_df = pd.DataFrame({
                'Company Ticker': allocation.keys(),
                'Discrete Allocation': discrete_allocation_list
            })

            file_path = f"Portafolios/Max Sharpe {current_date}.xlsx"
            portfolio_df.to_excel(file_path, index=False)
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover, "Max Sharpe")

        def max_return(self):

            ef = EfficientFrontier(self.mu, self.s)

            weights = ef.max_quadratic_utility()
            cleaned_weights = ef.clean_weights()

            performance = ef.portfolio_performance(verbose=True, risk_free_rate=self.rf)
            expected_return, volatility, sharpe_ratio = performance

            latest_prices = get_latest_prices(df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.portafolio)
            allocation, leftover = da.lp_portfolio()

            discrete_allocation_list = [allocation[symbol] for symbol in allocation]

            portfolio_df = pd.DataFrame({
                'Company Ticker': allocation.keys(),
                'Discrete Allocation': discrete_allocation_list
            })

            file_path = f"Portafolios/Max Return {current_date}.xlsx"
            portfolio_df.to_excel(file_path, index=False)
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover, "Max Return")


        def min_vol(self):

            ef = EfficientFrontier(self.mu, self.s)

            weights = ef.min_volatility()
            cleaned_weights = ef.clean_weights()

            performance = ef.portfolio_performance(verbose=True, risk_free_rate=self.rf)
            expected_return, volatility, sharpe_ratio = performance

            latest_prices = get_latest_prices(df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.portafolio)
            allocation, leftover = da.lp_portfolio()

            discrete_allocation_list = [allocation[symbol] for symbol in allocation]

            portfolio_df = pd.DataFrame({
                'Company Ticker': allocation.keys(),
                'Discrete Allocation': discrete_allocation_list
            })

            file_path = f"Portafolios/Min Vol {current_date}.xlsx"
            portfolio_df.to_excel(file_path, index=False)
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover, "Min Vol")


        def target_return(self, target_return):

            ef = EfficientFrontier(self.mu, self.s)

            weights = ef.efficient_return(target_return)
            cleaned_weights = ef.clean_weights()

            performance = ef.portfolio_performance(verbose=True, risk_free_rate=self.rf)
            expected_return, volatility, sharpe_ratio = performance

            latest_prices = get_latest_prices(df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.portafolio)
            allocation, leftover = da.lp_portfolio()

            discrete_allocation_list = [allocation[symbol] for symbol in allocation]

            portfolio_df = pd.DataFrame({
                'Company Ticker': allocation.keys(),
                'Discrete Allocation': discrete_allocation_list
            })

            file_path = f"Portafolios/Target Return {current_date}.xlsx"
            portfolio_df.to_excel(file_path, index=False)
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover, f"Target Return of {target_return}")



        def target_vol(self, target_vol):

            ef = EfficientFrontier(self.mu, self.s)

            weights = ef.efficient_risk(target_vol)
            cleaned_weights = ef.clean_weights()

            performance = ef.portfolio_performance(verbose=True, risk_free_rate=self.rf)
            expected_return, volatility, sharpe_ratio = performance

            latest_prices = get_latest_prices(df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.portafolio)
            allocation, leftover = da.lp_portfolio()

            discrete_allocation_list = [allocation[symbol] for symbol in allocation]

            portfolio_df = pd.DataFrame({
                'Company Ticker': allocation.keys(),
                'Discrete Allocation': discrete_allocation_list
            })

            file_path = f"Portafolios/Target Vol {current_date}.xlsx"
            portfolio_df.to_excel(file_path, index=False)
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover, f"Target Vol of {target_vol}")

    return PortfolioOptimization(mu, s, portafolio, rf)
