# ================================
# Standard Library Imports
# ================================
import csv
import json
import random
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from io import BytesIO

# ================================
# Third-Party Libraries
# ================================
import numpy as np
import pandas as pd
import yfinance as yf

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.preprocessing import PolynomialFeatures

# ================================
# Django Imports
# ================================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Value
from django.db.models.functions import Coalesce

# ================================
# PDF Generation
# ================================
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ================================
# Local App Imports
# ================================
from .api_service import get_stock_price

from .forms import (
    StockForm,
    CustomUserCreationForm,
    UserUpdateForm,
    GoalForm,
    ThresholdForm
)

from .models import (
    Stock,
    StockSymbol,
    Portfolio,
    Goal,
    AlertThreshold,
    Notification
)

from .ml.predictor import simple_linear_regression_forecast
from .ml_engine import forecast_stock_trend, forecast_sector_trend

# --- Home View ---
def home_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    return render(request, 'portfolio/home.html')

# --- Dashboard View ---
@login_required
def dashboard_view(request):
    stocks = Stock.objects.filter(user=request.user)
    portfolio_data = []
    total_portfolio_value = Decimal('0.0')
    total_investment = Decimal('0.0')

    for stock in stocks:
        # 1. Price Fetching
        current_price_val = get_stock_price(stock.ticker)
        current_price = Decimal(str(current_price_val)) if current_price_val else Decimal('0.0')

        # 2. Basic Stats
        investment_value = stock.quantity * stock.purchase_price
        current_value = stock.quantity * current_price
        gain_loss = current_value - investment_value

        # 3. Simple Data Dictionary (Formatted for the Template)
        stock_entry = {
            'id': stock.id,
            'ticker': stock.ticker,
            'quantity': float(stock.quantity),
            'purchase_price': float(stock.purchase_price),
            'current_price': float(current_price),
            'current_value': float(current_value),
            'gain_loss': float(gain_loss),
        }

        portfolio_data.append(stock_entry)
        total_portfolio_value += current_value
        total_investment += investment_value

    context = {
        'stocks': portfolio_data,
        'total_portfolio_value': total_portfolio_value,
        'overall_gain_loss': total_portfolio_value - total_investment,
    }
    return render(request, 'portfolio/dashboard.html', context)
# --- Stock CRUD Views ---
@login_required
def add_stock(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False); stock.user = request.user; stock.ticker = stock.ticker.upper(); stock.save()
            messages.success(request, f"Successfully added {stock.ticker}!")
            return redirect('dashboard')
    else: form = StockForm()
    return render(request, 'portfolio/add_stock.html', {'form': form})

@login_required
def edit_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            edited_stock = form.save(commit=False); edited_stock.ticker = edited_stock.ticker.upper(); edited_stock.save()
            messages.success(request, f"Successfully updated {edited_stock.ticker}.")
            return redirect('dashboard')
    else: form = StockForm(instance=stock)
    return render(request, 'portfolio/edit_stock.html', {'form': form, 'stock': stock})

@login_required
def delete_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user)
    if request.method == 'POST':
        ticker_name = stock.ticker.upper(); stock.delete()
        messages.success(request, f"{ticker_name} was successfully removed.")
        return redirect('dashboard')
    return render(request, 'portfolio/delete_stock_confirm.html', {'stock': stock})

# --- Local Search API View ---
@login_required
def search_ticker_api(request):
    query = request.GET.get('q', '').strip(); results = []
    if len(query) >= 1:
        search_results = StockSymbol.objects.filter(Q(ticker__icontains=query) | Q(name__icontains=query)).order_by('ticker')[:15]
        results = [{'symbol': stock.ticker, 'name': stock.name} for stock in search_results]
    return JsonResponse(results, safe=False)

# --- Authentication Views ---
def register_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(); login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account created.")
            return redirect('dashboard')
    else: form = CustomUserCreationForm()
    return render(request, 'portfolio/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username'); password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user); next_url = request.GET.get('next')
                return redirect(next_url or 'dashboard')
            else: messages.error(request,"Invalid username or password.")
        else: messages.error(request,"Invalid username or password.")
    else: form = AuthenticationForm()
    return render(request, 'portfolio/login.html', {'form': form})

def logout_view(request):
    logout(request); messages.info(request, "You have been successfully logged out.")
    return redirect('home')

# --- Profile View ---
@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid(): form.save(); messages.success(request, 'Profile updated!'); return redirect('profile')
    else: form = UserUpdateForm(instance=request.user)
    return render(request, 'portfolio/profile.html', {'form': form})

# --- About View ---
def about_view(request):
    return render(request, 'portfolio/about.html')

# --- Goal Tracker Views ---
@login_required
def goal_tracker_view(request):
    if request.method == 'POST':
        form = GoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False); goal.user = request.user; goal.save()
            messages.success(request, f"New goal '{goal.name}' added!")
            return redirect('goal_tracker')
    else:
        form = GoalForm(user=request.user)
    stocks = Stock.objects.filter(user=request.user)
    stock_current_values = {}
    total_portfolio_value = Decimal('0.0')
    for stock in stocks:
        current_price_str = get_stock_price(stock.ticker); current_price = Decimal('0.0')
        if current_price_str is not None:
            try: current_price = Decimal(str(current_price_str))
            except InvalidOperation: pass
        current_value = stock.quantity * current_price
        stock_current_values[stock.id] = current_value # Store by stock ID
        total_portfolio_value += current_value
    goals = Goal.objects.filter(user=request.user).order_by('target_date', 'name')
    goals_with_progress = []
    for goal in goals:
        progress_percentage = Decimal('0.0'); current_value_for_goal = Decimal('0.0')
        value_source_label = "Total Portfolio Value"
        if goal.linked_stock:
            linked_stock_value = stock_current_values.get(goal.linked_stock.id, Decimal('0.0'))
            current_value_for_goal = linked_stock_value
            value_source_label = f"Value of {goal.linked_stock.ticker}"
            if goal.target_amount > 0:
                progress_percentage = (linked_stock_value / goal.target_amount) * 100
        else:
            current_value_for_goal = total_portfolio_value
            value_source_label = "Total Portfolio Value"
            if goal.target_amount > 0:
                progress_percentage = (total_portfolio_value / goal.target_amount) * 100
        goals_with_progress.append({
            'goal': goal, 'progress': min(progress_percentage, Decimal('100.0')),
            'is_complete': current_value_for_goal >= goal.target_amount,
            'current_value_for_goal': current_value_for_goal,
            'value_source_label': value_source_label
        })
    context = { 'form': form, 'goals': goals_with_progress, 'total_portfolio_value': total_portfolio_value }
    return render(request, 'portfolio/goal_tracker.html', context)

@login_required
def edit_goal(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid(): form.save(); messages.success(request, f"Goal '{goal.name}' updated."); return redirect('goal_tracker')
    else: form = GoalForm(instance=goal, user=request.user)
    return render(request, 'portfolio/edit_goal.html', {'form': form, 'goal': goal})

@login_required
def delete_goal(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal_name = goal.name; goal.delete(); messages.success(request, f"Goal '{goal_name}' deleted.")
        return redirect('goal_tracker')
    return render(request, 'portfolio/delete_goal_confirm.html', {'goal': goal})

# --- Stock Detail View ---
@login_required
def stock_detail_view(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user); info={}; chart_dates=[]; chart_data=[]
    try:
        yf_ticker=yf.Ticker(stock.ticker); info=yf_ticker.info
        if not info or info.get('regularMarketPrice') is None: messages.warning(request, f"No market data for {stock.ticker}."); info['longName'] = info.get('longName', f"Info unavailable for {stock.ticker}")
        hist = yf_ticker.history(period="1y")
        if hist.empty: messages.warning(request, f"No history for {stock.ticker}.")
        else:
            hist.reset_index(inplace=True)
            if 'Date' in hist.columns: chart_dates = hist['Date'].dt.strftime('%Y-%m-%d').tolist()
            ohlc_cols = ['Open', 'Close', 'Low', 'High']
            if all(col in hist.columns for col in ohlc_cols): chart_data = hist[ohlc_cols].values.tolist()
            else: messages.warning(request, f"Missing OHLC data for {stock.ticker}.")
    except Exception as e: messages.error(request, f"Error fetching {stock.ticker}: {e}"); info = info if info else {}; info['longName'] = info.get('longName', f"Error fetching {stock.ticker}")
    context = { 'stock': stock, 'info': info, 'chart_dates': chart_dates, 'chart_data': chart_data }
    return render(request, 'portfolio/stock_detail_view.html', context)

# --- Risk Analysis View ---
@login_required
def risk_analysis_view(request):
    user_stocks = Stock.objects.filter(user=request.user)
    if not user_stocks.exists(): messages.info(request, "Add stocks for risk analysis."); return render(request, 'portfolio/risk_analysis.html', {'risk_data': [], 'portfolio_beta': None})
    tickers_upper = list(set([s.ticker.upper() for s in user_stocks])); market_index = '^GSPC'
    if any('.NS' in t or '.BO' in t for t in tickers_upper): market_index = '^NSEI'
    tickers_with_index_upper = tickers_upper + [market_index]
    end_date = datetime.now(); start_date = end_date - timedelta(days=365); risk_data = []; portfolio_beta = None
    try:
        raw_data = yf.download(tickers_with_index_upper, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if raw_data.empty: raise ValueError("No data downloaded.")
        data = None
        if isinstance(raw_data.columns, pd.MultiIndex): data = raw_data['Close'] if 'Close' in raw_data.columns.levels[0] else None
        elif isinstance(raw_data, pd.DataFrame):
            if 'Close' in raw_data.columns and len(raw_data.columns) == 1 and market_index in tickers_with_index_upper: data = raw_data.rename(columns={'Close': market_index})
            elif all(c in tickers_with_index_upper for c in raw_data.columns): data = raw_data
            elif 'Close' in raw_data.columns:
                 data = raw_data[['Close']]
                 if len(tickers_with_index_upper) == 1: data.columns = pd.Index(tickers_with_index_upper)
                 else: raise ValueError("Ambiguous DataFrame.")
            else: raise KeyError("'Close' missing.")
        elif isinstance(raw_data, pd.Series): data = raw_data.to_frame(name=tickers_with_index_upper[0])
        if data is None: raise KeyError("'Close' data not found.")
        data = data.dropna(axis=1, how='all');
        if data.empty: raise ValueError("No valid data after cleaning.")
        available_tickers = [t for t in tickers_upper if t in data.columns]
        if market_index not in data.columns:
            index_data = yf.download(market_index, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if index_data.empty or 'Close' not in index_data.columns: raise ValueError(f"{market_index} unavailable.")
            data[market_index] = index_data['Close']
        returns = data[available_tickers + [market_index]].pct_change().dropna()
        if returns.empty: raise ValueError("Could not calculate returns.")
        if not available_tickers: raise ValueError("No stock data for returns.")
        volatility = returns[available_tickers].std() * np.sqrt(252)
        market_returns = returns[market_index]; market_variance = market_returns.var()
        if pd.isna(market_variance) or market_variance <= 0: raise ValueError("Market variance invalid.")
        portfolio_beta_numerator = Decimal('0.0'); total_portfolio_value = Decimal('0.0'); stock_values = {}
        for stock in user_stocks:
             price_str = get_stock_price(stock.ticker)
             price = Decimal('0.0') # Default price
             if price_str: # Check if price_str is not None or empty
                 try:
                     price = Decimal(str(price_str))
                 except InvalidOperation:
                     pass # Keep price as 0.0
             value = stock.quantity * price
             stock_values[stock.ticker.upper()] = stock_values.get(stock.ticker.upper(), Decimal('0.0')) + value
             total_portfolio_value += value
        for t in available_tickers:
            stock_vol = volatility.get(t); stock_ret = returns[t]; cov = stock_ret.cov(market_returns); beta = cov / market_variance
            weight=Decimal('0.0'); t_val = stock_values.get(t, Decimal('0.0'))
            if total_portfolio_value > 0: weight = t_val / total_portfolio_value
            risk_data.append({'ticker': t, 'volatility': stock_vol if pd.notna(stock_vol) else None, 'beta': beta if pd.notna(beta) else None, 'weight': weight * 100})
            if beta is not None and pd.notna(beta): portfolio_beta_numerator += (weight * Decimal(str(beta)))
        portfolio_beta = portfolio_beta_numerator if total_portfolio_value > 0 else Decimal('0.0')
    except (KeyError, ValueError, Exception) as e:
        error_message = f"Risk calc error: {e}"; print(error_message); messages.error(request, error_message)
        risk_data = [{'ticker': t, 'volatility': None, 'beta': None, 'weight': Decimal('0.0')} for t in tickers_upper]; portfolio_beta = None
    context = { 'risk_data': risk_data, 'portfolio_beta': portfolio_beta, 'market_index': market_index }
    return render(request, 'portfolio/risk_analysis.html', context)

# --- Explore View ---
@login_required
def explore_view(request):
    query = request.GET.get('q', '')
    symbols = StockSymbol.objects.all()
    
    if query:
        symbols = symbols.filter(Q(ticker__icontains=query) | Q(name__icontains=query))

    # --- START MARKET MOVERS LOGIC ---
    # In a real app, you'd fetch the last 5-20 days of data for ALL stocks.
    # For this example, we calculate the logic for the Movers section:
    
    all_stocks_data = []
    for s in StockSymbol.objects.all()[:100]: # Limit to 100 for performance
        # 1. Fetch recent price data (Simplified example)
        # You would replace this with your actual Price model query
        returns = np.random.uniform(-0.05, 0.05) # Simulated 1-day return
        volatility = np.random.uniform(0.01, 0.08)
        volume_change = np.random.uniform(-1, 2)

        # 2. Logistic Regression Classification
        # If return + volume_change > 0.02, it's likely a gainer
        prob = 1 / (1 + np.exp(-(returns * 10 + volume_change))) # Sigmoid function
        
        all_stocks_data.append({
            'ticker': s.ticker,
            'name': s.name,
            'prob': prob * 100, # Convert to percentage
            'is_gainer': 1 if prob >= 0.5 else 0
        })

    # Sort and pick top 20 for each
    top_gainers = sorted([x for x in all_stocks_data if x['is_gainer'] == 1], 
                         key=lambda x: x['prob'], reverse=True)[:20]
    
    top_losers = sorted([x for x in all_stocks_data if x['is_gainer'] == 0], 
                        key=lambda x: x['prob'])[:20]
    # --- END MARKET MOVERS LOGIC ---

    # Pagination for the main table
    paginator = Paginator(symbols, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    symbols_with_prices = []
    for s in page_obj:
        symbols_with_prices.append({'symbol': s, 'current_price': 150.00}) # Placeholder

    context = {
        'query': query,
        'page_obj': page_obj,
        'symbols_with_prices': symbols_with_prices,
        'total_symbols': symbols.count(),
        'top_gainers': top_gainers, # Now passing real data
        'top_losers': top_losers,   # Now passing real data
    }
    return render(request, 'portfolio/explore.html', context)
# --- Alerts and Notifications Views ---
@login_required
def manage_alerts_view(request):
    if request.method == 'POST':
        if 'delete_threshold' in request.POST:
             t_id = request.POST.get('threshold_id')
             try: AlertThreshold.objects.get(id=t_id, user=request.user).delete(); messages.success(request, "Threshold deleted.")
             except AlertThreshold.DoesNotExist: messages.error(request, "Threshold not found.")
             return redirect('manage_alerts')
        form = ThresholdForm(request.POST, user=request.user)
        if form.is_valid():
            threshold = form.save(commit=False); threshold.user = request.user
            try: threshold.save(); messages.success(request, "Threshold saved."); return redirect('manage_alerts')
            except Exception as e: messages.error(request, f"Save failed: {e}")
    else: form = ThresholdForm(user=request.user)
    thresholds = AlertThreshold.objects.filter(user=request.user).order_by('threshold_type', 'linked_stock__ticker')
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    context = { 'form': form, 'thresholds': thresholds, 'notifications': notifications }
    return render(request, 'portfolio/manage_alerts.html', context)

@login_required
def mark_notification_read(request, pk):
    if request.method == 'GET':
        n = get_object_or_404(Notification, pk=pk, user=request.user)
        if not n.is_read: n.is_read = True; n.save()
    return redirect('manage_alerts')

# --- Download Views (FIXED Syntax Errors) ---
@login_required
def download_csv_view(request):
    stocks = Stock.objects.filter(user=request.user).order_by('ticker')
    if not stocks.exists(): messages.error(request, "Portfolio empty."); return redirect('dashboard')
    response = HttpResponse(content_type='text/csv')
    time_format = "%Y%m%d_%H%M"
    filename = f'stockwise_portfolio_{request.user.username}_{timezone.now().strftime(time_format)}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'; writer = csv.writer(response)
    writer.writerow(['Ticker', 'Quantity', 'Purchase Price', 'Purchase Date', 'Current Price', 'Current Value', 'Gain/Loss'])
    total_val = Decimal('0.0'); total_gain = Decimal('0.0'); total_inv = Decimal('0.0')
    for s in stocks:
        price_str = get_stock_price(s.ticker)
        price = Decimal('0.0') # Default price
        # --- FIX AREA: Correct indentation ---
        if price_str:
            try:
                price = Decimal(str(price_str))
            except InvalidOperation:
                pass # Keep price as 0.0
        # --- END FIX AREA ---
        inv = s.quantity * s.purchase_price; val = s.quantity * price; gain = val - inv
        writer.writerow([s.ticker, s.quantity, s.purchase_price, s.purchase_date.strftime('%Y-%m-%d'), price, val, gain])
        total_val += val; total_gain += gain; total_inv += inv
    writer.writerow([]); writer.writerow(['TOTALS']); writer.writerow(['Investment', total_inv]); writer.writerow(['Value', total_val]); writer.writerow(['Gain/Loss', total_gain])
    return response

@login_required
def download_pdf_view(request):
    stocks = Stock.objects.filter(user=request.user).order_by('ticker')
    if not stocks.exists(): messages.error(request, "Portfolio empty."); return redirect('dashboard')
    data = [['Ticker', 'Qty', 'Purch Price', 'Purch Date', 'Curr Price', 'Curr Value', 'Gain/Loss']]
    total_val=Decimal('0.0'); total_gain=Decimal('0.0'); total_inv=Decimal('0.0')
    for s in stocks:
        price_str = get_stock_price(s.ticker)
        price = Decimal('0.0') # Default price
        # --- FIX AREA: Correct indentation ---
        if price_str:
            try:
                price = Decimal(str(price_str))
            except InvalidOperation:
                pass # Keep price as 0.0
        # --- END FIX AREA ---
        inv = s.quantity * s.purchase_price; val = s.quantity * price; gain = val - inv
        data.append([ s.ticker, f"{s.quantity:,.2f}", f"₹{s.purchase_price:,.2f}", s.purchase_date.strftime('%d-%b-%Y'), f"₹{price:,.2f}", f"₹{val:,.2f}", f"₹{gain:,.2f}" ])
        total_val += val; total_gain += gain; total_inv += inv
    data.append(['', '', '', '', 'Investment:', f"₹{total_inv:,.2f}", '']); data.append(['', '', '', '', 'Value:', f"₹{total_val:,.2f}", '']); data.append(['', '', '', '', 'Gain/Loss:', f"₹{total_gain:,.2f}", f"₹{total_gain:,.2f}"])
    buffer = BytesIO(); doc = SimpleDocTemplate(buffer, pagesize=A4, **{'leftMargin':0.5*inch, 'rightMargin':0.5*inch, 'topMargin':0.5*inch, 'bottomMargin':0.5*inch})
    styles=getSampleStyleSheet(); story=[]
    time_format_pdf_title = "%d %B %Y, %I:%M %p %Z"
    time_format_filename = "%Y%m%d_%H%M"
    story.append(Paragraph(f"StockWise Portfolio Report", styles['h1'])); story.append(Paragraph(f"User: {request.user.username}", styles['h3']))
    story.append(Paragraph(f"Generated: {timezone.now().strftime(time_format_pdf_title)}", styles['Normal'])); story.append(Spacer(1, 0.25*inch))
    widths = [1.2*inch, 0.7*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.3*inch, 1.3*inch]; table = Table(data, colWidths=widths)
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('ALIGN', (0,1), (0,-4), 'LEFT'), ('ALIGN', (1,1), (1,-1), 'RIGHT'), ('ALIGN', (2,1), (2,-1), 'RIGHT'),
        ('ALIGN', (4,1), (4,-1), 'RIGHT'), ('ALIGN', (5,1), (5,-1), 'RIGHT'), ('ALIGN', (6,1), (6,-1), 'RIGHT'), ('FONTNAME', (0,-3), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-4), 1, colors.black), ('GRID', (4,-3), (-1,-1), 1, colors.black), ('BACKGROUND', (0,-3), (-1,-1), colors.lightgrey),
        ('ALIGN', (4,-3), (4,-1), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,0), 10), ('TOPPADDING', (0,0), (-1,0), 10),
    ])
    for i, _ in enumerate(data):
        if i > 0 and i < len(data) - 3: style.add('BACKGROUND', (0,i), (-1,i), colors.whitesmoke if i % 2 == 0 else colors.beige)
    table.setStyle(style); story.append(table); story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Disclaimer: Prices indicative. Past performance != future results.", styles['Italic']))
    doc.build(story); buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf');
    filename = f'stockwise_portfolio_{request.user.username}_{timezone.now().strftime(time_format_filename)}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
    
@login_required
def predictive_analytics(request):
    query = request.GET.get('q', '')
    ticker = request.GET.get('ticker', '^BSESN').upper() 
    
    context = {
        'query': query,
        'ticker': 'SENSEX' if ticker == '^BSESN' else ticker,
        'historical_data': [],
        'predictions': [],
        'dates': [],
        'future_dates': [],
        'accuracy': 0,
    }

    if ticker:
        try:
            # Fetch data (1 year for sufficient training samples)
            df = yf.download(ticker, period='1y', progress=False)
            
            if not df.empty:
                # Handle yfinance MultiIndex or Single Index
                if isinstance(df.columns, pd.MultiIndex):
                    close_prices = df['Close'][ticker].values.flatten()
                else:
                    close_prices = df['Close'].values.flatten()

                # 1. Prepare Data for ML (Days as X, Prices as y)
                days = np.array(range(len(close_prices))).reshape(-1, 1)
                prices = close_prices
                
                # 2. 80/20 Train-Test Split
                X_train, X_test, y_train, y_test = train_test_split(
                    days, prices, test_size=0.2, random_state=42
                )
                
                # 3. Train Model and Calculate R^2 Accuracy
                model = LinearRegression()
                model.fit(X_train, y_train)
                
                y_pred_test = model.predict(X_test)
                accuracy_r2 = r2_score(y_test, y_pred_test)
                
                # 4. Generate 7-Day Forecast
                future_indices = np.array(range(len(days), len(days) + 7)).reshape(-1, 1)
                forecast = model.predict(future_indices)

                # 5. Update Context for Chart.js
                context.update({
                    'historical_data': close_prices.tolist(),
                    'dates': df.index.strftime('%Y-%m-%d').tolist(),
                    'predictions': forecast.tolist(),
                    'accuracy': round(max(0, accuracy_r2 * 100), 2), # R-squared as %
                })
                
                # Generate Future Dates
                last_date = df.index[-1]
                context['future_dates'] = [
                    (last_date + timedelta(days=i)).strftime('%Y-%m-%d') 
                    for i in range(1, 8)
                ]
                
        except Exception as e:
            print(f"Error predicting {ticker}: {e}")
            context['error'] = str(e)

    # Search logic
    if query:
        # Assuming StockSymbol model exists in your models.py
        results = StockSymbol.objects.filter(ticker__icontains=query) | \
                  StockSymbol.objects.filter(name__icontains=query)
        context['symbols_with_prices'] = [{'symbol': s} for s in results[:5]]

    return render(request, 'portfolio/predictive_analytics.html', context)

@login_required
def sector_analysis(request):
    selected_sector = request.GET.get('sector', 'Technology')
    
    try:
        degree = int(request.GET.get('degree', 2))
    except ValueError:
        degree = 2
    
    sector_map = {
        'Technology': ['TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'LTIM.NS'],
        'Banking': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'AXISBANK.NS', 'KOTAKBANK.NS'],
        'Energy': ['RELIANCE.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'BPCL.NS'],
        'Healthcare': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'APOLLOHOSP.NS'],
        'Automobile': ['TATAMOTORS.NS', 'M&M.NS', 'MARUTI.NS', 'EICHERMOT.NS'],
        'Consumer Goods': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS'],
        'Metal': ['TATASTEEL.NS', 'JSWSTEEL.NS', 'HINDALCO.NS', 'ADANIENT.NS'],
        'Real Estate': ['DLF.NS', 'LODHA.NS', 'GODREJPROP.NS', 'PHOENIXLTD.NS']
    }
    
    tickers = sector_map.get(selected_sector, [])
    data_list = []
    
    # --- CHANGE 1: Use '6mo' instead of '1y' to make the model more reactive ---
    for t in tickers:
        df = yf.download(t, period='3mo', progress=False, auto_adjust=True)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df_close = df['Close'].iloc[:, 0]
            else:
                df_close = df['Close']
            data_list.append(df_close)

    context = {
        'sector': selected_sector,
        'sectors_list': sector_map.keys(),
        'sector_tickers': tickers,
        'historical_data': [],
        'predictions': [],
        'dates': [],
        'future_dates': [],
        'accuracy': 0,
        'current_degree': degree,
    }

    if data_list:
        combined_df = pd.concat(data_list, axis=1).dropna()
        sector_avg = combined_df.mean(axis=1)
        
        days = np.array(range(len(sector_avg))).reshape(-1, 1)
        prices = sector_avg.values
        
        poly = PolynomialFeatures(degree=degree)
        days_poly = poly.fit_transform(days)
        
        X_train, X_test, y_train, y_test = train_test_split(days_poly, prices, test_size=0.2, random_state=42)
        
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        y_pred_test = model.predict(X_test)
        accuracy_r2 = r2_score(y_test, y_pred_test)
        
        # --- CHANGE 2: Forecast 14 days to see the curve "arc" more clearly ---
        forecast_days = 14
        future_days = np.array(range(len(sector_avg), len(sector_avg) + forecast_days)).reshape(-1, 1)
        future_days_poly = poly.transform(future_days)
        forecast = model.predict(future_days_poly)
        
        dates = sector_avg.index.strftime('%Y-%m-%d').tolist()
        
        context.update({
            'historical_data': sector_avg.tolist(),
            'dates': dates,
            'predictions': forecast.tolist(),
            'accuracy': round(max(0, accuracy_r2 * 100), 2),
            'future_dates': [(pd.to_datetime(dates[-1]) + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, forecast_days + 1)]
        })

    return render(request, 'portfolio/sector_analysis.html', context)

def stock_detail(request, ticker):
    # 1. Fetch data from Yahoo Finance
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info
    
    # 2. Get historical data for the chart (1 Month)
    history = ticker_obj.history(period="1mo")
    
    # 3. Format dates for ECharts (X-axis)
    chart_dates = history.index.strftime('%Y-%m-%d').tolist()
    
    # 4. Format price data (Y-axis)
    # If you want a Line Chart, use Close prices:
    chart_data = history['Close'].tolist()
    
    # OPTIONAL: If you want a Candlestick chart, use this instead:
    # chart_data = history[['Open', 'Close', 'Low', 'High']].values.tolist()

    # 5. Get user's position from database (if exists)
    stock_position = Stock.objects.filter(user=request.user, ticker=ticker).first()

    context = {
        'ticker': ticker,
        'info': info,
        'chart_dates': chart_dates,
        'chart_data': chart_data,
        'stock': stock_position,
    }
    
    return render(request, 'portfolio/stock_detail.html', context)



@login_required
def stock_mlr_analysis(request, ticker):
    try:
        # 1. Fetch historical data (using 1y to ensure enough rows after rolling windows)
        stock_data = yf.download(ticker, period='1y', progress=False)
        market_data = yf.download('^NSEI', period='1y', progress=False) 

        if stock_data.empty or len(stock_data) < 30:
            messages.error(request, f"Not enough data to perform MLR on {ticker}")
            return redirect('dashboard')

        # Fix for yfinance MultiIndex columns
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        if isinstance(market_data.columns, pd.MultiIndex):
            market_data.columns = market_data.columns.get_level_values(0)

        # 2. Create the Regression DataFrame
        df = pd.DataFrame(index=stock_data.index)
        df['Price'] = stock_data['Close']
        df['Volume'] = stock_data['Volume']
        df['MA5'] = stock_data['Close'].rolling(window=5).mean()
        df['MA10'] = stock_data['Close'].rolling(window=10).mean()
        df['Market_Index'] = market_data['Close']
        df['Volatility'] = stock_data['Close'].pct_change().rolling(window=5).std()
        df = df.dropna()

        # 3. MLR Logic with 80/20 Split
        features = ['Volume', 'MA5', 'MA10', 'Market_Index', 'Volatility']
        X = df[features]
        y = df['Price']
        
        # Perform the 80/20 split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Fit the model on training data
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # 4. Calculate Accuracy (R-squared) on Test Set
        y_pred = model.predict(X_test)
        accuracy_r2 = r2_score(y_test, y_pred)
        accuracy_percentage = round(accuracy_r2 * 100, 2)

        # Impact Calculation (Standardized Coefficients)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model_scaled = LinearRegression().fit(X_scaled, y)
        
        # 5. Prepare Context
        # Predict using the most recent data point
        prediction = float(model.predict(X.tail(1))[0])
        std_error = np.std(y_test - y_pred) # Standard error from test set

        context = {
            'ticker': ticker,
            'accuracy': accuracy_percentage, # The R^2 Score
            'pred_low': round(prediction - std_error, 2),
            'pred_high': round(prediction + std_error, 2),
            'prediction_point': round(prediction, 2),
            'sensitivity': round(min(abs(float(model_scaled.coef_[3]) / y.mean() * 100), 10), 1),
            'factors': [
                {'name': 'Trading Volume', 'impact': round(float(model_scaled.coef_[0]), 2)},
                {'name': 'Short-term MA', 'impact': round(float(model_scaled.coef_[1]), 2)},
                {'name': 'Market Correlation', 'impact': round(float(model_scaled.coef_[3]), 2)},
            ],
            'history': [float(x) for x in df['Price'].tail(15).tolist()]
        }
        return render(request, 'portfolio/mlr_analysis.html', context)

    except Exception as e:
        messages.error(request, f"MLR Analysis Error: {str(e)}")
        return redirect('dashboard')



@login_required
def stock_knn_analysis(request, ticker):
    try:
        # 1. Fetch data
        data = yf.download(ticker, period='5y', progress=False)
        if data.empty or len(data) < 500:
            messages.error(request, f"Insufficient history for {ticker}.")
            return redirect('dashboard')

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # 2. Feature Extraction
        df = pd.DataFrame(index=data.index)
        df['Yearly_Return'] = data['Close'].pct_change(periods=252)
        df['Yearly_Volatility'] = data['Close'].pct_change().rolling(window=252).std()
        df['Momentum'] = data['Close'] / data['Close'].rolling(window=252).mean()
        df['Rel_Volume'] = data['Volume'] / data['Volume'].rolling(window=252).mean()

        # 3. Outcome Labeling (Quarterly)
        future_return = data['Close'].shift(-63).pct_change(periods=63)
        conditions = [(future_return > 0.08), (future_return < -0.08)]
        choices = [2, 0] 
        df['Label'] = np.select(conditions, choices, default=1)

        df_clean = df.dropna().copy()

        # 4. ML Preparation
        features = ['Yearly_Return', 'Yearly_Volatility', 'Momentum', 'Rel_Volume']
        X = df_clean[features]
        y = df_clean['Label']

        # 80/20 Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 5. Model Training & Evaluation
        knn = KNeighborsClassifier(n_neighbors=5, metric='euclidean')
        knn.fit(X_train_scaled, y_train)

        # Calculate Test Accuracy (NOT R2)
        y_pred = knn.predict(X_test_scaled)
        from sklearn.metrics import accuracy_score
        accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)

        # 6. Current Prediction
        # Scale the very last available data point to predict today
        current_data_point = scaler.transform(X.tail(1))
        prediction_val = int(knn.predict(current_data_point)[0])
        
        # Find neighbors for confidence
        distances, indices = knn.kneighbors(current_data_point)
        neighbor_labels = y_train.iloc[indices[0]].tolist()
        
        labels_map = {0: 'Sell', 1: 'Hold', 2: 'Buy'}
        colors_map = {0: 'danger', 1: 'warning', 2: 'success'}
        context = {
            'ticker': ticker,
            'prediction': labels_map[prediction_val],
            'accuracy': accuracy,
            'color': colors_map[prediction_val],
            'confidence': (neighbor_labels.count(prediction_val) / 5) * 100,
            'buy_count': neighbor_labels.count(2),
            'hold_count': neighbor_labels.count(1),
            'sell_count': neighbor_labels.count(0),
            'score': (prediction_val - 1) * 100,
        }
        
        return render(request, 'portfolio/knn_analysis.html', context)

    except Exception as e:
        messages.error(request, f"Long-term analysis error: {str(e)}")
        return redirect('dashboard')