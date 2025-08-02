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

        items = request.POST.getlist('items[]')
        serials = request.POST.getlist('serials[]')
        configs = request.POST.getlist('configs[]')
        complaints = request.POST.getlist('complaints[]')
        complaint_notes = request.POST.getlist('complaint_notes[]')

        for item_index, item in enumerate(items):
            if not item:
                continue

            # Get data for this item
            serial = serials[item_index] if item_index < len(serials) else ''
            config = configs[item_index] if item_index < len(configs) else ''
            complaint = complaints[item_index] if item_index < len(complaints) else ''
            note = complaint_notes[item_index] if item_index < len(complaint_notes) else ''

            # Create JobCard
            job = JobCard.objects.create(
                customer=customer,
                address=address,
                phone=phone,
                item=item,
                serial=serial,
                config=config,
                complaint_description=complaint,
                complaint_notes=note
            )

            # Handle images for this item
            image_field = f'images-{item_index}[]'
            images = request.FILES.getlist(image_field)
            for img in images:
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
        return redirect('jobcard_edit', pk=job.pk)

    return render(request, 'jobcard_edit.html', {'jobcard': job})