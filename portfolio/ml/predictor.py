import numpy as np

def simple_linear_regression_forecast(prices, future_days=7):

    if len(prices) < 2:
        return []

    X = np.arange(len(prices))
    Y = np.array(prices)

    # slope (m) and intercept (b)
    m = np.cov(X, Y)[0][1] / np.var(X)
    b = np.mean(Y) - m * np.mean(X)

    future_X = np.arange(len(prices), len(prices) + future_days)
    predictions = m * future_X + b

    return predictions.round(2).tolist()