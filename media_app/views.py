from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from leads_app.models import Lead, LeadProduct
from products.models import Category, Subcategory
from django.contrib.auth.models import User


def google_drive_url(url):
    """
    Convert Google Drive sharing link to thumbnail URL for better embedding reliability.
    Input: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    Output: https://drive.google.com/thumbnail?id=FILE_ID&sz=w400 (thumbnail format)
    """
    import logging
    logger = logging.getLogger(__name__)

    if not url or not isinstance(url, str):
        logger.warning(f"Invalid URL provided: {url}")
        return url

    # Skip invalid entries like "No Photo"
    if url.strip().lower() in ['no photo', 'n/a', 'none', '']:
        logger.warning(f"Skipping invalid image URL entry: {url}")
        return None  # Return None to indicate invalid URL

    logger.info(f"Processing Google Drive URL: {url}")

    # Check if it's a Google Drive sharing link
    if 'drive.google.com/file/d/' in url and '/view?usp=sharing' in url:
        # Extract file ID from the URL
        start = url.find('/file/d/') + 8
        end = url.find('/view?usp=sharing')
        if start != -1 and end != -1 and start < end:
            file_id = url[start:end]

            # Use thumbnail URL instead of uc?export=view for better embedding
            # Thumbnail URLs are more reliable for web embedding
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
            logger.info(f"✅ Converted Google Drive URL to thumbnail: {url} -> {thumbnail_url}")
            return thumbnail_url

    # Check if it's already a thumbnail URL
    if 'drive.google.com/thumbnail?' in url and 'id=' in url:
        logger.info(f"✅ Already a thumbnail URL: {url}")
        return url

    # Check if it's already a direct Google Drive URL (convert to thumbnail)
    if 'drive.google.com/uc?' in url and 'id=' in url:
        # Extract file ID and convert to thumbnail
        id_start = url.find('id=') + 3
        id_end = url.find('&', id_start) if '&' in url[id_start:] else len(url)
        if id_start != -1:
            file_id = url[id_start:id_end]
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
            logger.info(f"✅ Converted uc URL to thumbnail: {url} -> {thumbnail_url}")
            return thumbnail_url

    # Return original URL if not a Google Drive link
    logger.warning(f"❌ Not a recognized Google Drive URL format: {url}")
    return url


def check_google_drive_accessibility(url):
    """
    Check if a Google Drive URL is accessible and return status info.
    """
    import requests
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Try a HEAD request first (lighter than GET)
        response = requests.head(url, timeout=10, allow_redirects=True)
        logger.info(f"Google Drive URL {url} returned status {response.status_code}")

        if response.status_code == 200:
            return {'accessible': True, 'status': response.status_code}
        else:
            return {'accessible': False, 'status': response.status_code, 'reason': 'Non-200 status code'}

    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to check Google Drive URL {url}: {e}")
        return {'accessible': False, 'error': str(e), 'reason': 'Request failed'}


@login_required
def media_gallery(request):
    """Display all images in a paginated grid with filters"""

    # Base queryset - get all images from leads and lead products
    lead_images = Lead.objects.exclude(images__isnull=True).exclude(images='')
    lead_product_images = LeadProduct.objects.exclude(image__isnull=True).exclude(image='')
    google_drive_images = Lead.objects.exclude(image_url__isnull=True).exclude(image_url='')

    # Combine all images with their metadata
    all_images = []

    # Process lead images
    for lead in lead_images:
        if lead.images:
            all_images.append({
                'image_url': lead.images.url,
                'client_name': lead.contact_name,
                'company_name': lead.company_name,
                'category_name': lead.category.name if lead.category else 'N/A',
                'product_name': ', '.join([p.name for p in lead.products_enquired.all()]) if lead.products_enquired.exists() else 'N/A',
                'salesperson': lead.assigned_sales_person.get_full_name() if lead.assigned_sales_person else lead.assigned_sales_person.username if lead.assigned_sales_person else 'Unassigned',
                'created_date': lead.created_date,
                'image_type': 'lead_image',
                'lead_id': lead.id,
            })

    # Process lead product images
    for lead_product in lead_product_images:
        if lead_product.image:
            all_images.append({
                'image_url': lead_product.image.url,
                'client_name': lead_product.lead.contact_name,
                'company_name': lead_product.lead.company_name,
                'category_name': lead_product.category.name if lead_product.category else 'N/A',
                'product_name': lead_product.subcategory.name if lead_product.subcategory else 'N/A',
                'salesperson': lead_product.lead.assigned_sales_person.get_full_name() if lead_product.lead.assigned_sales_person else lead_product.lead.assigned_sales_person.username if lead_product.lead.assigned_sales_person else 'Unassigned',
                'created_date': lead_product.created_date,
                'image_type': 'product_image',
                'lead_id': lead_product.lead.id,
            })

    # Process Google Drive images
    for lead in google_drive_images:
        if lead.image_url:
            converted_url = google_drive_url(lead.image_url)
            # Skip if URL conversion returned None (invalid URL)
            if converted_url is None:
                continue

            all_images.append({
                'image_url': converted_url,
                'client_name': lead.contact_name,
                'company_name': lead.company_name,
                'category_name': lead.category.name if lead.category else 'N/A',
                'product_name': ', '.join([p.name for p in lead.products_enquired.all()]) if lead.products_enquired.exists() else 'N/A',
                'salesperson': lead.assigned_sales_person.get_full_name() if lead.assigned_sales_person else lead.assigned_sales_person.username if lead.assigned_sales_person else 'Unassigned',
                'created_date': lead.created_date,
                'image_type': 'google_drive',
                'lead_id': lead.id,
            })

    # Apply filters
    date_filter = request.GET.get('date_filter', '')
    salesperson_filter = request.GET.get('salesperson_filter', '')

    if date_filter:
        from datetime import datetime, timedelta
        today = datetime.now().date()
        if date_filter == 'today':
            filtered_images = [img for img in all_images if img['created_date'].date() == today]
        elif date_filter == 'week':
            week_ago = today - timedelta(days=7)
            filtered_images = [img for img in all_images if img['created_date'].date() >= week_ago]
        elif date_filter == 'month':
            month_ago = today - timedelta(days=30)
            filtered_images = [img for img in all_images if img['created_date'].date() >= month_ago]
        else:
            filtered_images = all_images
    else:
        filtered_images = all_images

    if salesperson_filter:
        if salesperson_filter == 'unassigned':
            filtered_images = [img for img in filtered_images if img['salesperson'] == 'Unassigned']
        else:
            filtered_images = [img for img in filtered_images if str(img.get('salesperson_id', img['salesperson'])) == salesperson_filter]

    # Sort by creation date (newest first)
    filtered_images.sort(key=lambda x: x['created_date'], reverse=True)

    # Pagination - 20 images per page (5x4 grid)
    paginator = Paginator(filtered_images, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get all salespeople for filter dropdown
    salespeople = User.objects.filter(
        Q(assigned_leads__isnull=False) |
        Q(created_leads__isnull=False)
    ).distinct().order_by('first_name', 'last_name')

    context = {
        'page_obj': page_obj,
        'images': page_obj.object_list,
        'total_images': len(filtered_images),
        'date_filter': date_filter,
        'salesperson_filter': salesperson_filter,
        'salespeople': salespeople,
    }

    return render(request, 'media_app/media_gallery.html', context)
