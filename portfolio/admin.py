from django.contrib import admin
from .models import Stock

# This class customizes the admin interface for the Stock model
class StockAdmin(admin.ModelAdmin):
    # Fields to display in the main list view of stocks
    list_display = ('user', 'ticker', 'quantity', 'purchase_price', 'purchase_date')
    
    # Fields that can be used to filter the list of stocks
    list_filter = ('user', 'purchase_date')
    
    # Fields that the search bar will look through
    search_fields = ('ticker', 'user__username')
    
    # Default ordering of the list
    ordering = ('-purchase_date',)

# Register your Stock model with the custom admin class
admin.site.register(Stock, StockAdmin)