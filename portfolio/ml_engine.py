import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
def forecast_stock_trend(historical_data):
    """
    Accepts a Pandas DataFrame with 'Close' prices.
    Returns a 7-day projection.
    """
    # Prepare data
    df = historical_data.copy()
    df['Day'] = np.arange(len(df))
    
    X = df[['Day']].values
    y = df['Close'].values
    
    # Simple Linear Regression (Line of Best Fit)
    model = LinearRegression()
    model.fit(X, y)
    
    # Project 7 days into the future
    future_days = np.array([len(df) + i for i in range(1, 8)]).reshape(-1, 1)
    predictions = model.predict(future_days)
    
    return predictions

def forecast_sector_trend(list_of_dfs):
    """
    Normalizes multiple stocks to a base of 100 to show 'Trend Percentage' 
    rather than raw price, then applies Polynomial Regression.
    """
    # 1. Combine and handle missing data
    combined_df = pd.concat([df['Close'] for df in list_of_dfs], axis=1).dropna()
    
    # 2. Normalize: (Price / First Price) * 100 
    # This shows the % growth of the sector over time
    normalized_df = (combined_df / combined_df.iloc[0]) * 100
    sector_index = normalized_df.mean(axis=1)
    
    # 3. Polynomial Regression (Degree 2)
    y = sector_index.values
    X = np.arange(len(y)).reshape(-1, 1)
    
    model = make_pipeline(PolynomialFeatures(degree=2), Ridge(alpha=1.0))
    model.fit(X, y)
    
    # 4. Forecast 7 Days
    future_X = np.array([len(y) + i for i in range(1, 8)]).reshape(-1, 1)
    predictions = model.predict(future_X)
    
    return sector_index.tolist(), sector_index.index.strftime('%Y-%m-%d').tolist(), predictions.tolist()