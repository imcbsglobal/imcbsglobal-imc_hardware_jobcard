from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import JobCard, JobCardImage
import os

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

def jobcard_edit(request, pk):
    job = get_object_or_404(JobCard, pk=pk)

    if request.method == 'POST':
        try:
            # Update basic fields
            job.customer = request.POST.get('customer', '').strip()
            job.address = request.POST.get('address', '').strip()
            job.phone = request.POST.get('phone', '').strip()
            job.item = request.POST.get('item', job.item)
            job.serial = request.POST.get('serial', '')
            job.config = request.POST.get('config', '')
            job.complaint_description = request.POST.get('complaint_description', '')
            job.complaint_notes = request.POST.get('complaint_notes', '')
            job.save()

            # Handle image deletions
            for img_id in request.POST.getlist('delete_images'):
                try:
                    img = get_object_or_404(JobCardImage, id=img_id, jobcard=job)
                    if img.image and os.path.isfile(img.image.path):
                        os.remove(img.image.path)
                    img.delete()
                except:
                    pass

            # Handle new images
            new_images = request.FILES.getlist('new_images[]')
            for img in new_images:
                JobCardImage.objects.create(jobcard=job, image=img)

            messages.success(request, 'Job card updated successfully.')
            # ✅ FIXED: Redirect to jobcard_list instead of back to edit page
            return redirect('jobcard_list')

        except Exception as e:
            messages.error(request, f'Error updating job card: {str(e)}')
            return render(request, 'jobcard_edit.html', {'jobcard': job})

    return render(request, 'jobcard_edit.html', {'jobcard': job})