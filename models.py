from django.db import models


class Wallet(models.Model):
    address = models.CharField(max_length=255)
    centrality = models.FloatField(default=0.0)
    clustering = models.FloatField(default=0.0)
    total_transactions = models.IntegerField(default=0) 
    suspicious_transaction_count = models.IntegerField(default=0)
    genuine_transaction_count = models.IntegerField(default=0)
    suspicious = models.BooleanField(default=False)
    def __str__(self):
        return self.address


class Transaction(models.Model):
    sender = models.CharField(max_length=255)
    receiver = models.CharField(max_length=255)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    suspicious = models.BooleanField(default=False)
