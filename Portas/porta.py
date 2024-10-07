def get_df():

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

    # Function to read stock symbols from a file
    def read_stock_symbols(file_path):
        with open(file_path, 'r') as file:
            return file.read().splitlines()

    # Function to fetch adjusted close prices for given symbols
    def fetch_adj_close_prices(symbols):
        adj_close_list = []
        for symbol in symbols:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="max")

            # Reset index to work with the datetime as a column
            hist.reset_index(inplace=True)

            # Extract only the date, ignoring the hour
            hist['Date'] = hist['Date'].dt.date

            # Group by date and take the last closing price of each day
            daily_data = hist.groupby('Date').agg({'Close': 'last'}).rename(columns={'Close': symbol})
            
            # Append the data to the list
            adj_close_list.append(daily_data)

        # Concatenate all data along the columns axis
        return pd.concat(adj_close_list, axis=1)


    # Function to generate all possible trading dates
    def generate_all_dates(start_date, end_date):
        return pd.date_range(start=start_date, end=end_date, freq='B').date

    current_date = datetime.now().strftime("%Y-%m-%d")

    csv_file = f"{current_date}.csv"

    if not os.path.exists(csv_file):
        # Read stock symbols from file
        stock_symbols = read_stock_symbols('ETFS&Stocks.txt')
        stock_symbols.insert(0, '^GSPC')  # Add S&P 500 index symbol

        # Fetch data for all stock symbols
        df = fetch_adj_close_prices(stock_symbols)

        # Get the minimum and maximum dates from the fetched data
        min_date = df.index.min()
        max_date = df.index.max()

        # Generate a complete list of business dates
        all_dates = pd.DataFrame(generate_all_dates(min_date, max_date), columns=['Date'])

        # Merge the generated dates with the fetched data, filling missing values
        df.reset_index(inplace=True)  # Reset index to make 'Date' a column
        merged_df = all_dates.merge(df, on='Date', how='left')

        # Filter out the dates where the S&P 500 index (^GSPC) has missing values
        # merged_df = merged_df[merged_df['^GSPC'].notna()]

        # Set 'Date' as index again for saving to CSV
        merged_df.set_index('Date', inplace=True)

        # Save the cleaned data to a CSV
        merged_df.to_csv(csv_file, index=True)

    df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)

    # Ensure the "Results" folder exists
    if not os.path.exists("Portafolios"):
        os.makedirs("Portafolios")

    # No se porque con estas da error
    columns_to_drop = [
        "AAXJ", "ACWI", "BIL", "BOTZ", "DIA", "EEM", "EWZ", "FAS", "GDX", "GLD",
        "IAU", "ICLN", "INDA", "IVV", "KWEB", "LIT", "MCHI", "NAFTRACISHRS.MX", "PSQ", "QCLN"
    ]

    # Drop the columns
    df.drop(columns=columns_to_drop, inplace=True)

    return df

def remove_etfs(df):    
# Read the column names from ETFS.txt
    # Additional columns to drop
    additional_columns_to_drop = [
        "SPY", "SQQQ", "TAN", "TECL", "TLT", "TNA", "TQQQ", "USO", "VEA", "VGT",
        "VNQ", "VOO", "VT", "VTI", "VWO", "VYM", "XLE", "XLF", "XLK", "XLV"
    ]

    # Drop the columns
    df.drop(columns=additional_columns_to_drop, inplace=True, errors='ignore')

    return df

def portapara(df, portafolio, days, rf):

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

    mxntodlls = .05
    portafolio = portafolio * mxntodlls

    rf = (1 + rf) ** (252 / days) - 1
    
    mu = expected_returns.mean_historical_return(df, frequency=days)
    s = risk_models.sample_cov(df, frequency=days)

    current_date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    def save_to_excel(file_path, expected_return, volatility, sharpe_ratio, rf, leftover):
        workbook = load_workbook(file_path)
        sheet = workbook.active

        sheet["E2"] = "Return"
        sheet["E3"] = "Volatility"
        sheet["E4"] = "Sharpe Ratio"
        sheet["E5"] = "Risk-Free Rate"
        sheet["E6"] = "Leftover"
        sheet["F2"] = expected_return
        sheet["F3"] = volatility
        sheet["F4"] = sharpe_ratio
        sheet["F5"] = rf
        sheet["F6"] = leftover

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
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover)

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
            save_to_excel(file_path, expected_return, volatility, sharpe_ratio, self.rf, leftover)

    return PortfolioOptimization(mu, s, portafolio, rf)
