from django import forms
from .models import DisciplinaryRecord

class DisciplinaryEditForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryRecord
        fields = ['student', 'subject', 'details', 'severity', 'term']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control form-control-enhanced', 'maxlength': 200}),
            'details': forms.Textarea(attrs={'class': 'form-control form-control-enhanced', 'rows': 4, 'maxlength': 1500}),
            'student': forms.Select(attrs={'class': 'form-control form-control-enhanced'}),
            'severity': forms.Select(attrs={'class': 'form-control form-control-enhanced'}),
            'term': forms.Select(attrs={'class': 'form-control form-control-enhanced'}),
        }
        labels = {
            'student': 'Target Student',
            'subject': 'Case Headline',
            'details': 'Detailed Narrative',
            'severity': 'Severity Level',
            'term': 'Academic Term (optional)',
        }


from django import forms
from .models import Exam, GradeScale, MarksEntry

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = '__all__'

class GradeScaleForm(forms.ModelForm):
    class Meta:
        model = GradeScale
        fields = '__all__'

class MarksEntryForm(forms.ModelForm):
    class Meta:
        model = MarksEntry
        fields = ['marks_obtained', 'grade', 'remarks']



from django import forms
from .models import CurriculumDevelopment

class CurriculumDevelopmentForm(forms.ModelForm):
    class Meta:
        model = CurriculumDevelopment
        fields = ['course', 'title', 'version', 'status', 'rationale']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Revised CS Curriculum'}),
            'version': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '1.0'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'rationale': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Reason for proposal or update...'}),
        }