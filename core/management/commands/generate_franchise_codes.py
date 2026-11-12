import re
from django.core.management.base import BaseCommand
from core.models import Franchise  # Adjust if your app/model is named differently

class Command(BaseCommand):
    help = 'Generate or update unique franchise codes without using numbers (uses initials only)'

    def handle(self, *args, **options):
        updated_count = 0

        all_existing_codes = set(
            Franchise.objects.exclude(franchise_code__isnull=True)
            .values_list('franchise_code', flat=True)
        )

        for franchise in Franchise.objects.all():
            if not franchise.name or not franchise.location:
                self.stdout.write(
                    self.style.WARNING(f"Skipping franchise ID {franchise.id} - missing name or location")
                )
                continue

            # Extract initials from name
            name_words = re.findall(r'\b[A-Za-z]+', franchise.name.upper())
            name_code = ''
            for word in name_words:
                if len(name_code) < 3:
                    name_code += word[0]
            name_code = name_code.ljust(3, 'X')  # Pad with 'X' if less than 3

            # Use first 3 letters from location
            location_code = franchise.location.upper().replace(" ", "")[:3]
            location_code = location_code.ljust(3, 'X')  # Pad with 'X' if less

            base_code = f"{name_code}/{location_code}"

            # Ensure uniqueness
            suffix = 0
            new_code = base_code
            while new_code in all_existing_codes:
                suffix += 1
                # Extend location code (no digits)
                extended_loc = franchise.location.upper().replace(" ", "")[:3 + suffix]
                new_code = f"{name_code}/{extended_loc}"

            # Update if changed
            if franchise.franchise_code != new_code:
                franchise.franchise_code = new_code
                franchise.save(update_fields=["franchise_code"])
                all_existing_codes.add(new_code)
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated code to "{new_code}" for franchise "{franchise.name}"')
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} franchise records"))