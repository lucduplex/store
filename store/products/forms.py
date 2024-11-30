from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class ChatForm(forms.Form):
    message = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Tapez votre message ici...'
    }))

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = UserProfile 
        fields = ['face_id']
        

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    num_tel = forms.CharField(required=True)
    adresse = forms.CharField(required=True)
    face_id = forms.ImageField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'num_tel', 'adresse', 'face_id', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
        
        # Sauvegarder les données dans le profil utilisateur après la création de l'utilisateur
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'num_tel': self.cleaned_data['num_tel'],
                'face_id': self.cleaned_data['face_id'],
                'address': self.cleaned_data['adresse'],
            }
        )
        return user
    
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile  
        fields = ['num_tel', 'face_id', 'address']
