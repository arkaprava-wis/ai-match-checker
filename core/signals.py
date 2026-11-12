# signals.py
import requests
import json
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Franchise

# Set up logging
logger = logging.getLogger(__name__)

def sync_franchise_to_api(sender, instance, created, **kwargs):
    """
    Signal to automatically sync franchise data to external API when a new franchise is created.
         
    This signal triggers after a Franchise instance is saved.
    - sender: The Franchise model class
    - instance: The actual Franchise instance being saved
    - created: Boolean indicating if this is a new instance
    - **kwargs: Additional keyword arguments
    """
    
    if not created:
        return
         
  
    instance.refresh_from_db()
         
    # API endpoint URL
    api_url = getattr(settings, 'FRANCHISE_SYNC_API_URL', 'http://127.0.0.1:8000/franchise/create/')
         
 
    franchise_data = prepare_franchise_data(instance)
         
    if not franchise_data:
        logger.warning(f"Skipping sync for franchise '{instance.name}' - missing required data")
        return
         
 
    try:
        send_franchise_to_api(api_url, franchise_data, instance)
    except Exception as e:
        logger.error(f"Failed to sync franchise '{instance.name}' to API: {str(e)}")


def prepare_franchise_data(franchise_instance):
    """
    Prepare franchise data in the format expected by the API.
    
    Args:
        franchise_instance: Franchise model instance
        
    Returns:
        dict: Formatted franchise data or None if required data is missing
    """
    try:
        # Check if required fields are present
        if not franchise_instance.state or not franchise_instance.district:
            logger.warning(f"Franchise '{franchise_instance.name}' missing state or district")
            return None
        
        franchise_data = {
            'name': franchise_instance.name,
            'email': franchise_instance.email,
            'mobile': franchise_instance.mobile,
            'alternate_mobile': franchise_instance.alternate_mobile,
            'owner': franchise_instance.owner,
            'short_name': franchise_instance.short_name,
            'gstid': franchise_instance.gstid,
            'city': franchise_instance.city,
            'state_name': franchise_instance.state.name,
            'district_name': franchise_instance.district.name,
            'pincode': franchise_instance.pincode,
            'no_of_students': franchise_instance.no_of_students or 0,
            'location': franchise_instance.location,
            'zone': franchise_instance.zone,
            'franchise_code':franchise_instance.franchise_code
        }
        print(franchise_data)
        
        return franchise_data
        
    except Exception as e:
        logger.error(f"Error preparing franchise data for '{franchise_instance.name}': {str(e)}")
        return None


def send_franchise_to_api(api_url, franchise_data, franchise_instance):
    """
    Send franchise data to the external API.
    
    Args:
        api_url: API endpoint URL
        franchise_data: Formatted franchise data
        franchise_instance: Original franchise instance for logging
    """
    headers = {
        'Content-Type': 'application/json',
        # Add authentication headers if needed
        # 'X-API-Key': getattr(settings, 'FRANCHISE_API_KEY', ''),
        # 'Authorization': 'Bearer ' + getattr(settings, 'FRANCHISE_API_TOKEN', ''),
    }
    
    try:
        response = requests.post(
            api_url,
            data=json.dumps(franchise_data),
            headers=headers,
            timeout=10  # 10 seconds timeout
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Successfully synced franchise '{franchise_instance.name}' to API")
            
            # Optionally store the external ID if the API returns it
            try:
                response_data = response.json()
                external_id = response_data.get('id')
                if external_id:
                    # You can add a field to store external_id if needed
                    # franchise_instance.external_id = external_id
                    # franchise_instance.save(update_fields=['external_id'])
                    logger.info(f"External ID for franchise '{franchise_instance.name}': {external_id}")
            except (ValueError, KeyError):
                pass
                
        else:
            error_message = f"API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_message += f": {error_data.get('error', response.text)}"
            except ValueError:
                error_message += f": {response.text}"
            
            logger.error(f"Failed to sync franchise '{franchise_instance.name}': {error_message}")
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout syncing franchise '{franchise_instance.name}' to API")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error syncing franchise '{franchise_instance.name}' to API at {api_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error syncing franchise '{franchise_instance.name}': {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error syncing franchise '{franchise_instance.name}': {str(e)}")



"""
from celery import shared_task

@shared_task
def sync_franchise_to_api_async(franchise_id):
    '''
    Asynchronous task to sync franchise to API using Celery.
    '''
    try:
        franchise = Franchise.objects.get(id=franchise_id)
        api_url = getattr(settings, 'FRANCHISE_SYNC_API_URL', 'http://127.0.0.1:8000/franchise/create/')
        franchise_data = prepare_franchise_data(franchise)
        
        if franchise_data:
            send_franchise_to_api(api_url, franchise_data, franchise)
    except Franchise.DoesNotExist:
        logger.error(f"Franchise with ID {franchise_id} not found")
    except Exception as e:
        logger.error(f"Error in async franchise sync: {str(e)}")

@receiver(post_save, sender=Franchise)
def sync_franchise_to_api_celery(sender, instance, created, **kwargs):
    '''
    Signal to trigger asynchronous franchise sync using Celery.
    '''
    if created:
        sync_franchise_to_api_async.delay(instance.id)
"""