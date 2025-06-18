from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Device
from django.contrib.auth import get_user_model  # Recommended approach

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['ship_name', 'owner_name', 'read_key', 'channel_id']
        widgets = {
            'ship_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'read_key': forms.TextInput(attrs={'class': 'form-control'}),
            'channel_id': forms.TextInput(attrs={'class': 'form-control'}),
        }