from django import forms


class WalletFetchForm(forms.Form):
    wallet_address = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter Bitcoin Wallet Address"
        })
    )
