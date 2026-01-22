from django import forms

class LargeTextarea(forms.Textarea):
    def __init__(self, attrs=None):
        default_attrs = {'rows': 6, 'cols': 80, 'style': 'width: 630px; height: 150px;'}

        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)