import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import quandl
import scipy.optimize as sco
import time
from IPython.display import Markdown, display


def hello():
    print("Hello")


def printmd(string):
    display(Markdown(string))


def getNordnetPositions(nordnetBrukerNavn, nordnetPassord):

    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from datetime import datetime  # Current date time in local system

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    browser = webdriver.Chrome(
        ChromeDriverManager().install(), options=chrome_options)

    browser.get(
        "https://classic.nordnet.no/mux/login/startNO.html?clearEndpoint=0&intent=next")
    print("Page title was '{}'".format(browser.title))
    time.sleep(5)

    switchToPasLogIn = browser.find_elements_by_xpath(
        '//button[starts-with(., "brukernavn og passord")]')[0].click()
    time.sleep(2)

    # Inserting values:
    logOnName = browser.find_elements_by_xpath(
        '//input')[0].send_keys(nordnetBrukerNavn)
    password = browser.find_elements_by_xpath(
        '//input')[1].send_keys(nordnetPassord)

    switchToPasLogIn = browser.find_elements_by_xpath(
        '//button[starts-with(., "Logg inn")]')[0].click()
    time.sleep(10)
    print("Page title was '{}'".format(browser.title))
    browser.get('https://www.nordnet.no/overview/details/3')
    print("Page title was '{}'".format(browser.title))
    tableRows = browser.find_elements_by_xpath('//tr')  # Find all rows
    stocks = []
    values = []
    for row in tableRows:
        tempData = row.text.split('\n')
        if len(tempData) >= 3:
            ticker, prct, value = tempData
            stocks.append(ticker)
            values.append(float(value.replace(" ", "")))
    browser.quit()
    df_temp = pd.DataFrame()
    df_temp['stock'] = stocks
    df_temp['value'] = values
    current_date = datetime.date(datetime.now())
    df_temp['date'] = current_date
    return df_temp


def yahooLink(start, end, ticker):
    return f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={start}&period2={end}&interval=1d&events=history"


def portfolio_annualised_performance(weights, mean_returns, cov_matrix):
    returns = np.sum(mean_returns*weights) * 252
    std = np.sqrt(np.dot(weights.T, np.dot(
        cov_matrix, weights))) * np.sqrt(252)
    return std, returns


def random_portfolios(num_portfolios, mean_returns, cov_matrix, risk_free_rate):
    results = np.zeros((3, num_portfolios))
    weights_record = []
    for i in range(num_portfolios):
        weights = np.random.random(num_assets)
        weights /= np.sum(weights)
        weights_record.append(weights)
        portfolio_std_dev, portfolio_return = portfolio_annualised_performance(
            weights, mean_returns, cov_matrix)
        results[0, i] = portfolio_std_dev
        results[1, i] = portfolio_return
        results[2, i] = (portfolio_return - risk_free_rate) / portfolio_std_dev
    return results, weights_record


def display_simulated_ef_with_random(table, mean_returns, cov_matrix, num_portfolios, risk_free_rate):
    results, weights = random_portfolios(
        num_portfolios, mean_returns, cov_matrix, risk_free_rate)

    max_sharpe_idx = np.argmax(results[2])
    sdp, rp = results[0, max_sharpe_idx], results[1, max_sharpe_idx]
    max_sharpe_allocation = pd.DataFrame(
        weights[max_sharpe_idx], index=table.columns, columns=['allocation'])
    max_sharpe_allocation.allocation = [
        round(i*100, 2)for i in max_sharpe_allocation.allocation]
    max_sharpe_allocation = max_sharpe_allocation.T

    min_vol_idx = np.argmin(results[0])
    sdp_min, rp_min = results[0, min_vol_idx], results[1, min_vol_idx]
    min_vol_allocation = pd.DataFrame(
        weights[min_vol_idx], index=table.columns, columns=['allocation'])
    min_vol_allocation.allocation = [
        round(i*100, 2)for i in min_vol_allocation.allocation]
    min_vol_allocation = min_vol_allocation.T

    print("-"*80)
    print("Maximum Sharpe Ratio Portfolio Allocation\n")
    print("Annualised Return:", round(rp, 2))
    print("Annualised Volatility:", round(sdp, 2))
    print("\n")
    print(max_sharpe_allocation)
    print("-"*80)
    print("Minimum Volatility Portfolio Allocation\n")
    print("Annualised Return:", round(rp_min, 2))
    print("Annualised Volatility:", round(sdp_min, 2))
    print("\n")
    print(min_vol_allocation)

    plt.figure(figsize=(10, 7))
    plt.scatter(results[0, :], results[1, :], c=results[2, :],
                cmap='YlGnBu', marker='o', s=10, alpha=0.3)
    plt.colorbar()
    plt.scatter(sdp, rp, marker='*', color='r',
                s=500, label='Maximum Sharpe ratio')
    plt.scatter(sdp_min, rp_min, marker='*', color='g',
                s=500, label='Minimum volatility')
    plt.title('Simulated Portfolio Optimization based on Efficient Frontier')
    plt.xlabel('annualised volatility')
    plt.ylabel('annualised returns')
    plt.legend(labelspacing=0.8)

# display_simulated_ef_with_random(mean_returns, cov_matrix, num_portfolios, risk_free_rate)


def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
    p_var, p_ret = portfolio_annualised_performance(
        weights, mean_returns, cov_matrix)
    return -(p_ret - risk_free_rate) / p_var


def max_sharpe_ratio(mean_returns, cov_matrix, risk_free_rate):
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix, risk_free_rate)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bound = (0.0, 1.0)
    bounds = tuple(bound for asset in range(num_assets))
    result = sco.minimize(neg_sharpe_ratio, num_assets*[
                          1./num_assets, ], args=args, method='SLSQP', bounds=bounds, constraints=constraints)
    return result


def portfolio_volatility(weights, mean_returns, cov_matrix):
    return portfolio_annualised_performance(weights, mean_returns, cov_matrix)[0]


def min_variance(mean_returns, cov_matrix):
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bound = (0.0, 1.0)
    bounds = tuple(bound for asset in range(num_assets))

    result = sco.minimize(portfolio_volatility, num_assets*[
                          1./num_assets, ], args=args, method='SLSQP', bounds=bounds, constraints=constraints)

    return result


def efficient_return(mean_returns, cov_matrix, target):
    num_assets = len(mean_returns)
    #args = (cov_matrix)

    def portfolio_return(weights):
        return - np.sum(mean_returns*weights) * 252

    def portfolio_volatility(weights):
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)

    constraints = ({'type': 'eq', 'fun': lambda x: portfolio_volatility(
        x) - target}, {'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for asset in range(num_assets))
    initialVal = num_assets*[1./num_assets, ]
    result = sco.minimize(portfolio_return, initialVal,
                          method='SLSQP', bounds=bounds, constraints=constraints)
    return result


def efficient_frontier(mean_returns, cov_matrix, volatility_range):
    efficients = []
    for ret in volatility_range:
        efficients.append(efficient_return(mean_returns, cov_matrix, ret))
    return efficients


def display_ef_with_selected(table, mean_returns, cov_matrix, risk_free_rate):
    returns = np.log(table) - np.log(table.shift(1))
    max_sharpe = max_sharpe_ratio(mean_returns, cov_matrix, risk_free_rate)
    sdp, rp = portfolio_annualised_performance(
        max_sharpe['x'], mean_returns, cov_matrix)
    max_sharpe_allocation = pd.DataFrame(
        max_sharpe.x, index=table.columns, columns=['allocation'])
    max_sharpe_allocation.allocation = [
        round(i*100, 2)for i in max_sharpe_allocation.allocation]
    max_sharpe_allocation = max_sharpe_allocation.T

    min_vol = min_variance(mean_returns, cov_matrix)
    sdp_min, rp_min = portfolio_annualised_performance(
        min_vol['x'], mean_returns, cov_matrix)
    min_vol_allocation = pd.DataFrame(
        min_vol.x, index=table.columns, columns=['allocation'])
    min_vol_allocation.allocation = [
        round(i*100, 2)for i in min_vol_allocation.allocation]
    min_vol_allocation = min_vol_allocation.T

    an_vol = np.std(returns) * np.sqrt(252)
    an_rt = mean_returns * 252

    print("-"*80)
    print("Maximum Sharpe Ratio Portfolio Allocation\n")
    print("Annualised Return:", round(rp, 2))
    print("Annualised Volatility:", round(sdp, 2))
    print("\n")
    print(max_sharpe_allocation)
    print("-"*80)
    print("Minimum Volatility Portfolio Allocation\n")
    print("Annualised Return:", round(rp_min, 2))
    print("Annualised Volatility:", round(sdp_min, 2))
    print("\n")
    print(min_vol_allocation)
    print("-"*80)
    print("Individual Stock Returns and Volatility\n")
    for i, txt in enumerate(table.columns):
        print(txt, ":", "annuaised return", round(
            an_rt[i], 2), ", annualised volatility:", round(an_vol[i], 2))
    print("-"*80)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(an_vol, an_rt, marker='o', s=200)

    for i, txt in enumerate(table.columns):
        ax.annotate(txt, (an_vol[i], an_rt[i]), xytext=(
            10, 0), textcoords='offset points')
    ax.scatter(sdp, rp, marker='*', color='r',
               s=500, label='Maximum Sharpe ratio')
    ax.scatter(sdp_min, rp_min, marker='*', color='g',
               s=500, label='Minimum volatility')

    targets = np.linspace(sdp_min, 0.19, 75)
    efficient_portfolios = efficient_frontier(
        mean_returns, cov_matrix, targets)
    returns_efficient = [portfolio_annualised_performance(
        p['x'], mean_returns, cov_matrix)[1] for p in efficient_portfolios]
    ax.plot(targets, returns_efficient, linestyle='-.',
            color='black', label='efficient frontier')
    ax.set_title('Portfolio Optimization with Individual Stocks')
    ax.set_xlabel('annualised volatility')
    ax.set_ylabel('annualised returns')
    ax.legend(labelspacing=0.8)


if __name__ == "__main__":
    import time
    import datetime
    import os
    import pickle
    import myFunctions

    df_full = pd.read_pickle("./data/stockData.pkl")
    data = pd.DataFrame()
    data['date'] = df_full['Date']
    data['ticker'] = df_full['ticker']
    data['adj_close'] = df_full['Adj Close']
    # data.head()
    df = data.set_index('date')
    table = df.pivot(columns='ticker')
    table.columns = ['Bonds', 'Agriculture', 'Emerging', 'Europe', 'Japan',
                     'US', 'Gold', 'Oil']  # table.columns = [col[1] for col in table.columns]
    table = table.dropna()

    returns = np.log(table) - np.log(table.shift(1))
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    num_portfolios = 50000
    risk_free_rate = 0.02

    display_ef_with_selected(table, mean_returns, cov_matrix, risk_free_rate)
    plt.show()
    print("end")
