from django.core.management.base import BaseCommand
from inventory.models import SellOrderItem, SellOrderReturn
from django.db.models import Sum

class Command(BaseCommand):
    help = "Update the delivered quantity of SellOrderItem objects based on their associated SellOrderReturn records."

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting the update of delivered quantities for returned sale order items...")

        # Fetch all SellOrderItems that have associated SellOrderReturn records
        sell_order_items = SellOrderItem.objects.filter(returns__isnull=False).distinct()

        for item in sell_order_items:
            # Calculate the total returned quantity for this SellOrderItem
            total_returned_quantity = SellOrderReturn.objects.filter(sell_order_item=item).aggregate(
                total=Sum('returned_quantity')
            )['total'] or 0

            # Update the delivered_quantity by subtracting the total returned quantity
            original_delivered_quantity = item.delivered_quantity
            item.delivered_quantity = max(0, original_delivered_quantity - total_returned_quantity)

            # Save the updated SellOrderItem
            item.save()

            self.stdout.write(
                f"Updated SellOrderItem (ID: {item.id}): "
                f"Original Delivered Quantity: {original_delivered_quantity}, "
                f"Total Returned Quantity: {total_returned_quantity}, "
                f"New Delivered Quantity: {item.delivered_quantity}"
            )

        self.stdout.write("Completed updating delivered quantities for returned sale order items.")