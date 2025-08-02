from django.db import models
import os
import uuid

class JobCard(models.Model):
    ITEM_CHOICES = [
        ('Mouse', 'Mouse'),
        ('Keyboard', 'Keyboard'),
        ('CPU', 'CPU'),
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
        ('Printer', 'Printer'),
        ('Monitor', 'Monitor'),
        ('Other', 'Other'),
    ]
    
    ticket_no = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    item = models.CharField(max_length=50, choices=ITEM_CHOICES)
    serial = models.CharField(max_length=100, blank=True, null=True)
    config = models.CharField(max_length=255, blank=True, null=True)
    complaint_description = models.TextField(blank=True, null=True)
    complaint_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer} - {self.item} ({self.ticket_no})"
    
    def save(self, *args, **kwargs):
        if not self.ticket_no:
            self.ticket_no = self.generate_ticket_number()
        super().save(*args, **kwargs)

    def generate_ticket_number(self):
        return f"TK-{uuid.uuid4().hex[:8].upper()}"

class JobCardImage(models.Model):
    jobcard = models.ForeignKey(JobCard, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='jobcard_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.jobcard.customer} - {self.jobcard.item}"

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)