from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Stock, Goal, AlertThreshold

# --- Form for Adding/Editing Stocks ---
class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['ticker', 'quantity', 'purchase_price', 'purchase_date']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'ticker': forms.TextInput(attrs={'autocomplete': 'off', 'placeholder': 'e.g., AAPL or RELIANCE.NS'}),
        }
        help_texts = {
            'ticker': 'Enter the official stock ticker symbol (e.g., AAPL for Apple, RELIANCE.NS for Reliance NSE).',
        }

# --- Custom Form for User Registration ---
class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(max_length=100, min_length=5, required=True, help_text='Required. 5 to 100 characters long.')
    email = forms.EmailField(required=True, help_text='Required. A valid email address is needed.')
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        forbidden_usernames = ['admin', 'support', 'root', 'administrator', 'contact', 'info', 'staff']
        if username.lower() in forbidden_usernames:
            raise forms.ValidationError("This username is reserved and cannot be used.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
             raise forms.ValidationError("This email address is already in use.")
        return email

# --- Form for Updating User Profile ---
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return email

# --- Form for Goal Tracker ---
class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'linked_stock', 'target_amount', 'target_date']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Buy a Car, Retirement Fund'}),
            'target_amount': forms.NumberInput(attrs={'placeholder': 'e.g., 500000'}),
        }
        labels = {
            'linked_stock': 'Link to Specific Stock (Optional)',
            'target_amount': 'Target Amount (₹)',
            'target_date': 'Target Date (Optional)',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(GoalForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['linked_stock'].queryset = Stock.objects.filter(user=user).order_by('ticker', 'purchase_date')
        self.fields['linked_stock'].required = False
        self.fields['linked_stock'].empty_label = "--- No specific stock ---"


# --- UPDATED: Form for Alert Thresholds ---
class ThresholdForm(forms.ModelForm):
    class Meta:
        model = AlertThreshold
        fields = ['threshold_type', 'linked_stock', 'threshold_value']
        labels = {
            'threshold_type': 'Alert Condition',
            'linked_stock': 'Specific Stock (if applicable)',
            'threshold_value': 'Threshold Value',
        }
        help_texts = {
            'linked_stock': 'Select only if creating a stock-specific alert (e.g., Stock Volatility). Leave blank for portfolio alerts.',
            'threshold_value': 'Enter the value to trigger the alert (e.g., 1.5 for Beta > 1.5, 0.4 for Volatility > 0.4).',
        }
        widgets = {
            'threshold_value': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        # --- FIX 1: Store the user on the form instance ---
        self.user = user
        # --- End FIX 1 ---
        super(ThresholdForm, self).__init__(*args, **kwargs)

        if user:
            self.fields['linked_stock'].queryset = Stock.objects.filter(user=user).order_by('ticker', 'purchase_date')
        else:
             self.fields['linked_stock'].queryset = Stock.objects.none()

        self.fields['linked_stock'].required = False
        self.fields['linked_stock'].empty_label = "--- Portfolio Alert ---"

    def clean(self):
        cleaned_data = super().clean()
        threshold_type = cleaned_data.get("threshold_type")
        linked_stock = cleaned_data.get("linked_stock")
        # --- FIX 2: Access the stored user directly ---
        user = self.user
        # --- End FIX 2 ---

        # Check for uniqueness constraint violation manually before save
        if user and threshold_type:
            filter_kwargs = {'user': user, 'threshold_type': threshold_type}
            if linked_stock:
                filter_kwargs['linked_stock'] = linked_stock
            else:
                filter_kwargs['linked_stock__isnull'] = True

            queryset = AlertThreshold.objects.filter(**filter_kwargs)
            if self.instance and self.instance.pk: # Exclude self if editing
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                error_msg = f"An alert threshold for '{dict(AlertThreshold.THRESHOLD_TYPES)[threshold_type]}' "
                if linked_stock: error_msg += f"on stock '{linked_stock.ticker}' "
                error_msg += "already exists."
                # Raise a validation error affecting the whole form or a specific field
                raise forms.ValidationError(error_msg, code='duplicate_threshold')


        # Require linked_stock only for stock-specific threshold types
        if threshold_type == 'STOCK_VOLATILITY_HIGH' and not linked_stock:
            self.add_error('linked_stock', "This field is required for a 'Stock Volatility' alert.")

        # Ensure linked_stock is empty for portfolio-level types
        if threshold_type == 'PORTFOLIO_BETA_HIGH' and linked_stock:
             # Clear the invalid selection instead of just adding an error
             cleaned_data['linked_stock'] = None
             # Optionally add an error message too if you want to explicitly tell the user
             self.add_error('linked_stock', "Specific stock should not be selected for a 'Portfolio Beta' alert.")


        return cleaned_data