# In portfolio/management/commands/load_stocks.py
import csv
from django.core.management.base import BaseCommand
from portfolio.models import StockSymbol

class Command(BaseCommand):
    help = 'Loads NSE stock symbols from a CSV file into the database'

    def handle(self, *args, **kwargs):
        csv_file_path = 'EQUITY_L.csv'
        self.stdout.write(f"Clearing existing stock symbols...")
        StockSymbol.objects.all().delete()

        self.stdout.write(f"Loading stocks from {csv_file_path}...")
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                symbols_to_create = [
                    StockSymbol(
                        ticker=row['SYMBOL'].strip() + ".NS",
                        name=row['NAME OF COMPANY'].strip()
                    )
                    for row in reader
                ]
                StockSymbol.objects.bulk_create(symbols_to_create)
            self.stdout.write(self.style.SUCCESS('Successfully loaded stock symbols.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file_path}."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))