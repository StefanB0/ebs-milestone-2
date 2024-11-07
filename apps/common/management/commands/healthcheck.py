import requests
import sys
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Perform health check"

    def handle(self, *args, **options):
        try:
            response = requests.get("http://localhost:8000/common/health", timeout=5)
            if response.status_code == 200:
                sys.exit(0)  # Healthy
            else:
                sys.exit(1)  # Unhealthy
        except requests.RequestException:
            sys.exit(1)  # Unhealthy
