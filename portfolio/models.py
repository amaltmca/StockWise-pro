from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone # Import timezone
import json

# --- Stock Model ---
class Stock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField()

    def __str__(self):
        # Provides a clearer name in dropdowns/admin
        return f"{self.ticker} (Purchased: {self.purchase_date})"

    price_history = models.TextField(blank=True, null=True)

    def set_price_history(self, price_list):
        self.price_history = json.dumps(price_list)

    def get_price_history(self):
          if self.price_history:
               return json.loads(self.price_history)
          return []

# --- StockSymbol Model ---
class StockSymbol(models.Model):
    ticker = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100, null=True, blank=True, db_index=True) # Sector field kept from previous steps

    def __str__(self):
        return f"{self.ticker} - {self.name}"

# --- Goal Model ---
class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    linked_stock = models.ForeignKey(
        Stock,
        on_delete=models.SET_NULL, # Keep goal even if stock is deleted
        null=True,
        blank=True,
        help_text="Optionally link this goal to a specific stock in your portfolio."
    )
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    target_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} (Target: {self.target_amount})"

# --- NEW: Model for User-Defined Alert Thresholds ---
class AlertThreshold(models.Model):
    THRESHOLD_TYPES = [
        ('PORTFOLIO_BETA_HIGH', 'Portfolio Beta Exceeds'),
        ('STOCK_VOLATILITY_HIGH', 'Stock Volatility Exceeds'),
        # Add more types later (e.g., price drop below value, goal progress % )
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alert_thresholds')
    threshold_type = models.CharField(max_length=50, choices=THRESHOLD_TYPES)
    # Optional: Link to a specific stock if it's a stock-specific threshold
    linked_stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=10, decimal_places=4, help_text="e.g., 1.5 for Beta, 0.4 for Volatility")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.linked_stock:
             return f"{self.user.username} - {self.get_threshold_type_display()} {self.threshold_value} for {self.linked_stock.ticker}"
        return f"{self.user.username} - {self.get_threshold_type_display()} {self.threshold_value}"

    class Meta:
        # Prevent duplicate thresholds of the same type (and stock if applicable) for the same user
        unique_together = ('user', 'threshold_type', 'linked_stock')

# --- NEW: Model for Generated Notifications ---
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True) # Index for faster filtering
    created_at = models.DateTimeField(default=timezone.now, db_index=True) # Index for faster ordering

    def __str__(self):
        read_status = "Read" if self.is_read else "Unread"
        return f"Notification for {self.user.username} ({read_status}) at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at'] # Show newest first by default

    # F:\stockwise1\portfolio\models.py

from django.db import models
from django.contrib.auth.models import User

class Portfolio(models.Model):  # Make sure this name matches exactly
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=20)
    quantity = models.FloatField()
    purchase_price = models.FloatField()
    purchase_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.ticker}"


