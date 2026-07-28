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