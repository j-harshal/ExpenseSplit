# splitwise_app/models.py
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100, unique=True)
    balance = models.FloatField(default=0.0)

    def __str__(self):
        return self.name

class Expense(models.Model):
    amount = models.FloatField()
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses_paid')
    split_type = models.CharField(max_length=10, choices=[('equal', 'Equal'), ('custom', 'Custom')])
    split_details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f'{self.amount} paid by {self.paid_by}'
