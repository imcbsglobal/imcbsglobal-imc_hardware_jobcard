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
    # Updated query to include all job cards with their images
    jobcards = JobCard.objects.all().prefetch_related('images').order_by('-created_at')
    return render(request, 'jobcard_list.html', {'jobcards': jobcards})

def jobcard_create(request):
    if request.method == 'POST':
        customer = request.POST.get('customer', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Validate required fields
        if not customer or not address or not phone:
            messages.error(request, "Customer name, address, and phone are required fields.")
            return redirect('jobcard_create')

        # Get all items and their indices
        items = request.POST.getlist('items[]')
        
        # Create a dictionary to organize items and their data
        items_data = {}
        for idx, item_name in enumerate(items):
            if not item_name:
                continue  # Skip empty items
            
            if item_name not in items_data:
                items_data[item_name] = {
                    'serial': request.POST.getlist('serials[]')[idx] if idx < len(request.POST.getlist('serials[]')) else '',
                    'config': request.POST.getlist('configs[]')[idx] if idx < len(request.POST.getlist('configs[]')) else '',
                    'complaints': []
                }
            
            # Get complaints for this item
            complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
            complaint_notes = request.POST.getlist(f'complaint_notes-{idx}[]')
            
            for complaint_idx, description in enumerate(complaint_descriptions):
                if not description.strip():
                    continue
                
                items_data[item_name]['complaints'].append({
                    'description': description,
                    'notes': complaint_notes[complaint_idx] if complaint_idx < len(complaint_notes) else '',
                    'images': request.FILES.getlist(f'images-{idx}-{complaint_idx}[]')
                })

        # Create job cards for each item and complaint
        for item_name, item_data in items_data.items():
            for complaint in item_data['complaints']:
                job_card = JobCard.objects.create(
                    customer=customer,
                    address=address,
                    phone=phone,
                    item=item_name,
                    serial=item_data['serial'],
                    config=item_data['config'],
                    complaint_description=complaint['description'],
                    complaint_notes=complaint['notes']
                )

                # Save images for this job card
                for image in complaint['images']:
                    JobCardImage.objects.create(jobcard=job_card, image=image)

        messages.success(request, "Job card(s) created successfully.")
        return redirect('jobcard_list')

    # For GET request, show the form with available items
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
        jobcards = JobCard.objects.filter(ticket_no=ticket_no)
        
        if not jobcards.exists():
            return JsonResponse({
                "success": False, 
                "error": f"No job cards found with ticket number: {ticket_no}"
            })
        
        deleted_count = 0
        
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

def jobcard_edit(request, pk):
    sample_job = get_object_or_404(JobCard, pk=pk)
    ticket_no = sample_job.ticket_no
    
    if request.method == 'POST':
        try:
            # Get customer info from form
            customer = request.POST.get('customer', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            ticket_no = request.POST.get('ticket_no', '').strip()

            # Validate required fields
            if not customer or not address or not phone:
                messages.error(request, "Customer name, address, and phone are required fields.")
                return redirect('jobcard_edit', pk=pk)

            # Get all existing job cards for this ticket
            existing_jobs = JobCard.objects.filter(ticket_no=ticket_no)
            
            # Get all items and their indices
            items = request.POST.getlist('items[]')
            complaint_ids = defaultdict(list)
            
            # Collect all complaint IDs from the form
            for idx, item_name in enumerate(items):
                if not item_name:
                    continue
                ids = request.POST.getlist(f'complaint_ids-{idx}[]')
                complaint_ids[idx] = ids

            # Delete job cards that were removed from the form
            for job in existing_jobs:
                found = False
                for idx, ids in complaint_ids.items():
                    if str(job.pk) in ids:
                        found = True
                        break
                if not found:
                    # Delete this job card and its images
                    for image in job.images.all():
                        if image.image and os.path.isfile(image.image.path):
                            os.remove(image.image.path)
                        image.delete()
                    job.delete()

            # Process each item in the form
            for idx, item_name in enumerate(items):
                if not item_name:
                    continue
                
                serial = request.POST.getlist('serials[]')[idx] if idx < len(request.POST.getlist('serials[]')) else ''
                config = request.POST.getlist('configs[]')[idx] if idx < len(request.POST.getlist('configs[]')) else ''
                
                # Get complaints for this item
                complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
                complaint_notes = request.POST.getlist(f'complaint_notes-{idx}[]')
                complaint_ids = request.POST.getlist(f'complaint_ids-{idx}[]')
                
                # Process each complaint
                for complaint_idx, description in enumerate(complaint_descriptions):
                    if not description.strip():
                        continue
                    
                    notes = complaint_notes[complaint_idx] if complaint_idx < len(complaint_notes) else ''
                    complaint_id = complaint_ids[complaint_idx] if complaint_idx < len(complaint_ids) else None
                    
                    if complaint_id:
                        # Update existing job card
                        job_card = JobCard.objects.filter(pk=complaint_id).first()
                        if job_card:
                            job_card.customer = customer
                            job_card.address = address
                            job_card.phone = phone
                            job_card.item = item_name
                            job_card.serial = serial
                            job_card.config = config
                            job_card.complaint_description = description
                            job_card.complaint_notes = notes
                            job_card.save()
                    else:
                        # Create new job card
                        job_card = JobCard.objects.create(
                            customer=customer,
                            address=address,
                            phone=phone,
                            item=item_name,
                            serial=serial,
                            config=config,
                            complaint_description=description,
                            complaint_notes=notes,
                            ticket_no=ticket_no
                        )
                    
                    # Handle images
                    images = request.FILES.getlist(f'images-{idx}-{complaint_idx}[]')
                    for image in images:
                        JobCardImage.objects.create(jobcard=job_card, image=image)
            
            # Handle deleted images
            delete_image_ids = request.POST.getlist('delete_images')
            for image_id in delete_image_ids:
                try:
                    image = JobCardImage.objects.get(pk=image_id)
                    if image.image and os.path.isfile(image.image.path):
                        os.remove(image.image.path)
                    image.delete()
                except JobCardImage.DoesNotExist:
                    pass

            messages.success(request, "Job card updated successfully.")
            return redirect('jobcard_list')
        
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('jobcard_edit', pk=pk)
    
    # For GET request, show the edit form
    all_jobcards = JobCard.objects.filter(ticket_no=ticket_no).prefetch_related('images').order_by('item', 'pk')
    
    if not all_jobcards.exists():
        messages.error(request, 'Job card not found.')
        return redirect('jobcard_list')
    
    first_job = all_jobcards.first()
    customer_info = {
        'customer': first_job.customer,
        'address': first_job.address,
        'phone': first_job.phone,
        'ticket_no': ticket_no
    }
    
    items_data = defaultdict(lambda: {
        'serial': '',
        'config': '',
        'complaints': []
    })
    
    for job in all_jobcards:
        if job.item not in items_data:
            items_data[job.item]['serial'] = job.serial
            items_data[job.item]['config'] = job.config
        
        items_data[job.item]['complaints'].append({
            'id': job.pk,
            'description': job.complaint_description,
            'notes': job.complaint_notes,
            'images': job.images.all()
        })

    context = {
        'customer_info': customer_info,
        'items_data': dict(items_data),
        'jobcards': all_jobcards,
        'pk': pk
    }
    
    return render(request, 'jobcard_edit.html', context)