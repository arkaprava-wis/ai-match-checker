from django import forms


from .models import  Role,Franchise,State,District


class RoleForm( forms.ModelForm):

    class Meta:
        model = Role
        fields = ('name', 'description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
         # Add styling to name field
        self.fields["name"].widget.attrs.update({
            "class": "form-control",
            "rows": 1,
            "style": "height: 50px"
        })
        # When we are update role disable name files
        if kwargs.get('instance'):
            self.fields['name'].widget.attrs.update({'onkeydown': 'return false;'})
            
            



        
class FranchiseForm(forms.ModelForm):
    class Meta:
        model = Franchise
        fields = [
            'name', 'image', 'email', 'mobile', 'owner', 'alternate_mobile',
            'short_name', 'gstid', 'state', 'city', 'pincode', 'district',
            'location', 'zone' ,'no_of_students' # New fields added here.
        ]
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'id': 'fancy-file-upload',
                'accept': '.jpg, .png, image/jpeg, image/png',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for state and district fields.
        self.fields['state'].queryset = State.objects.all().order_by('name')
        # Initially empty district queryset; it will be updated dynamically.
        self.fields['district'].queryset = District.objects.none()
        self.fields['gstid'].required = False

        if 'state' in self.data:
            try:
                state_id = int(self.data.get('state'))
                self.fields['district'].queryset = District.objects.filter(ref_state_id=state_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input; ignore and fallback to empty queryset
        elif self.instance.pk and self.instance.state:
            self.fields['district'].queryset = self.instance.state.districts.order_by('name')
        
        # Apply Bootstrap classes for styling.
        for field_name, field in self.fields.items():
            if field_name == 'image':
                continue
            existing_classes = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = f'{existing_classes} form-select'.strip()
            else:
                field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()



