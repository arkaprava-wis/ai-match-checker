# yourapp/management/commands/backfill_targets.py
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from inventory.models import SellOrder
from inventory.signals import rebuild_order_contributions

class Command(BaseCommand):
    help = "Back‑fill target achievements from SellOrders in a date range"

    def add_arguments(self, parser):
        parser.add_argument(
            '--start', required=True,
            help="Start date in YYYY‑MM‑DD"
        )
        parser.add_argument(
            '--end', required=True,
            help="End date in YYYY‑MM‑DD"
        )

    def handle(self, *args, **options):
        start = parse_date(options['start'])
        end   = parse_date(options['end'])
        qs = SellOrder.objects.filter(date__range=(start, end))

        total = qs.count()
        self.stdout.write(f"Found {total} orders between {start} and {end}")

        for idx, order in enumerate(qs, 1):
            rebuild_order_contributions(order)
            if idx % 50 == 0 or idx == total:
                self.stdout.write(f"  • Processed {idx}/{total}")

        self.stdout.write(self.style.SUCCESS(
            f"✅ Back‑filled target achievements for {total} orders."
        ))
