from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import JobCard, JobCardImage
import os
import json
from collections import defaultdict

def jobcard_list(request):
    jobcards = JobCard.objects.prefetch_related('images').order_by('-created_at')
    return render(request, 'jobcard_list.html', {'jobcards': jobcards})

def jobcard_create(request):
    if request.method == 'POST':
        customer = request.POST.get('customer', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Get all items and their indices
        items = request.POST.getlist('items[]')
        item_indices = range(len(items))
        
        # Group items by their name
        items_dict = {}
        for idx in item_indices:
            item_name = items[idx]
            if item_name not in items_dict:
                items_dict[item_name] = {
                    'serials': request.POST.getlist('serials[]')[idx] if idx < len(request.POST.getlist('serials[]')) else '',
                    'config': request.POST.getlist('configs[]')[idx] if idx < len(request.POST.getlist('configs[]')) else '',
                    'complaints': []
                }
            
            # Get all complaints for this item
            complaints = request.POST.getlist(f'complaints-{idx}[]')
            notes = request.POST.getlist(f'complaint_notes-{idx}[]')
            
            for complaint_idx, complaint in enumerate(complaints):
                items_dict[item_name]['complaints'].append({
                    'description': complaint,
                    'notes': notes[complaint_idx] if complaint_idx < len(notes) else '',
                    'images': request.FILES.getlist(f'images-{idx}-{complaint_idx}[]')
                })

        # Create job cards
        for item_name, item_data in items_dict.items():
            for complaint in item_data['complaints']:
                job = JobCard.objects.create(
                    customer=customer,
                    address=address,
                    phone=phone,
                    item=item_name,
                    serial=item_data['serials'],
                    config=item_data['config'],
                    complaint_description=complaint['description'],
                    complaint_notes=complaint['notes']
                )

                # Handle images for this complaint
                for img in complaint['images']:
                    JobCardImage.objects.create(jobcard=job, image=img)

        messages.success(request, "Job card(s) created successfully.")
        return redirect('jobcard_list')

    items = ["Mouse", "Keyboard", "CPU", "Laptop", "Desktop", "Printer", "Monitor", "Other"]
    return render(request, 'jobcard_form.html', {'items': items})

@require_POST
def delete_jobcard(request, pk):
    try:
        jobcard = get_object_or_404(JobCard, pk=pk)
        
        # Delete all associated images
        for image in jobcard.images.all():
            if image.image and os.path.isfile(image.image.path):
                os.remove(image.image.path)
            image.delete()
        
        jobcard.delete()
        return JsonResponse({"success": True, "message": "Deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@require_POST
def delete_ticket_by_number(request, ticket_no):
    try:
        # Get all job cards with this ticket number
        jobcards = JobCard.objects.filter(ticket_no=ticket_no)
        
        if not jobcards.exists():
            return JsonResponse({
                "success": False, 
                "error": f"No job cards found with ticket number: {ticket_no}"
            })
        
        deleted_count = 0
        
        # Delete all job cards with this ticket number
        for jobcard in jobcards:
            # Delete all associated images first
            for image in jobcard.images.all():
                if image.image and os.path.isfile(image.image.path):
                    try:
                        os.remove(image.image.path)
                    except OSError:
                        pass  # File might already be deleted
                image.delete()
            
            # Delete the job card
            jobcard.delete()
            deleted_count += 1
        
        return JsonResponse({
            "success": True, 
            "message": f"Successfully deleted {deleted_count} job card(s) with ticket number {ticket_no}"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": f"An error occurred while deleting ticket {ticket_no}: {str(e)}"
        })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import JobCard, JobCardImage
from collections import defaultdict

def jobcard_edit(request, pk):
    # Get the job card to determine ticket number
    sample_job = get_object_or_404(JobCard, pk=pk)
    ticket_no = sample_job.ticket_no
    
    # Get all job cards with the same ticket number
    all_jobcards = JobCard.objects.filter(ticket_no=ticket_no).prefetch_related('images').order_by('item', 'pk')
    
    if not all_jobcards.exists():
        messages.error(request, 'Job card not found.')
        return redirect('jobcard_list')
    
    # Get customer info from first job card
    first_job = all_jobcards.first()
    customer_info = {
        'customer': first_job.customer,
        'address': first_job.address,
        'phone': first_job.phone,
        'ticket_no': ticket_no
    }
    
    # Organize job cards by item for template
    items_data = defaultdict(lambda: {
        'serial': '',
        'config': '',
        'complaints': []
    })
    
    for job in all_jobcards:
        if job.item not in items_data:
            items_data[job.item] = {
                'serial': job.serial or '',
                'config': job.config or '',
                'complaints': []
            }
        
        # Add complaint data
        complaint_data = {
            'id': job.pk,
            'description': job.complaint_description or '',
            'notes': job.complaint_notes or '',
            'images': list(job.images.all())
        }
        items_data[job.item]['complaints'].append(complaint_data)
    
    context = {
        'customer_info': customer_info,
        'items_data': dict(items_data),
        'available_items': ["Mouse", "Keyboard", "CPU", "Laptop", "Desktop", "Printer", "Monitor", "Other"]
    }
    
    return render(request, 'jobcard_edit.html', context)