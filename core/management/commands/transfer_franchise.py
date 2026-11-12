import requests
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Franchise, State, District 


class Command(BaseCommand):
    help = 'Transfer franchises from current project to another project via bulk creation API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://194.164.151.111:8000/franchise/create-bulk/',
            help='The bulk creation API endpoint URL'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of franchises to process in each batch'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be transferred without actually making API calls'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(f'Starting franchise transfer to {api_url}')
        )

        try:
            # Get all franchises from current project
            franchises = Franchise.objects.select_related('state', 'district').all()
            
            if not franchises.exists():
                self.stdout.write(
                    self.style.WARNING('No franchises found in the current project')
                )
                return

            total_franchises = franchises.count()
            self.stdout.write(f'Found {total_franchises} franchises to transfer')

            # Process franchises in batches
            transferred_count = 0
            failed_count = 0
            
            for i in range(0, total_franchises, batch_size):
                batch = franchises[i:i + batch_size]
                batch_data = self.prepare_batch_data(batch)
                
                if dry_run:
                    self.stdout.write(
                        f'[DRY RUN] Would transfer batch {i//batch_size + 1} with {len(batch_data)} franchises'
                    )
                    for franchise_data in batch_data:
                        self.stdout.write(f'  - {franchise_data["name"]} ({franchise_data["state_name"]}, {franchise_data["district_name"]})')
                    transferred_count += len(batch_data)
                else:
                    success, message = self.send_batch_to_api(api_url, batch_data)
                    
                    if success:
                        transferred_count += len(batch_data)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully transferred batch {i//batch_size + 1} ({len(batch_data)} franchises)'
                            )
                        )
                    else:
                        failed_count += len(batch_data)
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to transfer batch {i//batch_size + 1}: {message}'
                            )
                        )

            # Summary
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[DRY RUN] Would transfer {transferred_count} franchises in {(total_franchises + batch_size - 1) // batch_size} batches'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Transfer complete! Successfully transferred: {transferred_count}, Failed: {failed_count}'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error during franchise transfer: {str(e)}')

    def prepare_batch_data(self, franchises):
        """
        Prepare franchise data for the bulk creation API
        """
        batch_data = []
        
        for franchise in franchises:
            franchise_data = {
                'name': franchise.name,
                'email': franchise.email,
                'mobile': franchise.mobile,
                'alternate_mobile': franchise.alternate_mobile,
                'owner': franchise.owner,
                'short_name': franchise.short_name,
                'gstid': franchise.gstid,
                'city': franchise.city,
                'state_name': franchise.state.name if franchise.state else '',
                'district_name': franchise.district.name if franchise.district else '',
                'pincode': franchise.pincode,
                'no_of_students': franchise.no_of_students or 0,
                'location': franchise.location,
                'zone': franchise.zone,
                'franchise_code':franchise.franchise_code
            }
            print(franchise_data)
            # Only add franchises with required state and district data
            if franchise_data['state_name'] and franchise_data['district_name']:
                batch_data.append(franchise_data)
              
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping franchise "{franchise.name}" - missing state or district data'
                    )
                )
        
        return batch_data

    def send_batch_to_api(self, api_url, batch_data):
        """
        Send batch data to the bulk creation API
        """
        payload = {
            'franchises': batch_data
        }
        
        headers = {
            'Content-Type': 'application/json',
         
        }

        try:
            response = requests.post(
                api_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=30 
            )
            
            if response.status_code == 201:
                response_data = response.json()
                return True, f"Created {response_data.get('total_franchises_created', len(batch_data))} franchises"
            else:
                error_message = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', error_message)
                except:
                    pass
                return False, f"API returned status {response.status_code}: {error_message}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout - API took too long to respond"
        except requests.exceptions.ConnectionError:
            return False, f"Connection error - could not reach API at {api_url}"
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"