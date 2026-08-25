from django.core.management.base import BaseCommand
from django.db import transaction
from attendance.models import MetadataCategory, MetadataValue

class Command(BaseCommand):
    help = 'Seed initial metadata categories and values from system models'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting metadata seeding...'))

        # 1. Define categories (system model mappings)
        categories_data = [
            {'name': 'ACADEMIC_TERMS', 'display': 'Academic Terms', 'model': 'academicterm'},
            {'name': 'FACULTIES', 'display': 'Faculties', 'model': 'faculty'},
            {'name': 'DEPARTMENTS', 'display': 'Departments', 'model': 'department'},
            {'name': 'COURSES', 'display': 'Courses', 'model': 'course'},
            {'name': 'STREAMS', 'display': 'Streams', 'model': 'stream'},
            {'name': 'COURSE_UNITS', 'display': 'Course Units', 'model': 'courseunit'},
            {'name': 'FEE_ELEMENTS', 'display': 'Fee Elements', 'model': 'feeelement'},
            {'name': 'GRADE_SCALES', 'display': 'Grade Scales', 'model': 'gradescale'},
            {'name': 'INSTITUTIONS', 'display': 'Institutions', 'model': 'institution'},
            {'name': 'CAMPUSES', 'display': 'Campuses', 'model': 'campus'},
            {'name': 'VEHICLES', 'display': 'Vehicles', 'model': 'vehicle'},
            {'name': 'HOSTELS', 'display': 'Hostels', 'model': 'hostel'},
            {'name': 'SUPPLIERS', 'display': 'Suppliers', 'model': 'supplier'},
        ]

        created_categories = 0
        for cat in categories_data:
            obj, created = MetadataCategory.objects.get_or_create(
                name=cat['name'],
                defaults={
                    'display_name': cat['display'],
                    'model_name': cat['model'],
                    'is_active': True
                }
            )
            if created:
                created_categories += 1
                self.stdout.write(f'  + Created category: {cat["display"]}')
            else:
                self.stdout.write(f'  - Category already exists: {cat["display"]}')

        self.stdout.write(self.style.SUCCESS(f'Categories: {created_categories} created, {len(categories_data)-created_categories} existing.'))

        # 2. Seed sample values for some key categories
        sample_values = {
            'ACADEMIC_TERMS': [
                {'value': '2024/2025_SEM1', 'display': 'Semester 1, 2024/2025', 'desc': 'First semester of academic year 2024/2025'},
                {'value': '2024/2025_SEM2', 'display': 'Semester 2, 2024/2025', 'desc': 'Second semester of academic year 2024/2025'},
            ],
            'FACULTIES': [
                {'value': 'FAC_SCI', 'display': 'Faculty of Science', 'desc': 'Science and technology'},
                {'value': 'FAC_ART', 'display': 'Faculty of Arts', 'desc': 'Humanities and social sciences'},
            ],
            'DEPARTMENTS': [
                {'value': 'DEPT_CS', 'display': 'Department of Computer Science', 'desc': 'Computing and IT'},
                {'value': 'DEPT_MATH', 'display': 'Department of Mathematics', 'desc': 'Mathematical sciences'},
            ],
            'COURSES': [
                {'value': 'BSC_CS', 'display': 'BSc in Computer Science', 'desc': 'Undergraduate CS'},
                {'value': 'BSC_MATH', 'display': 'BSc in Mathematics', 'desc': 'Undergraduate Mathematics'},
            ],
            'STREAMS': [
                {'value': 'STREAM_A', 'display': 'Stream A - Morning', 'desc': 'Morning session'},
                {'value': 'STREAM_B', 'display': 'Stream B - Evening', 'desc': 'Evening session'},
            ],
            'GRADE_SCALES': [
                {'value': 'UG_SCALE', 'display': 'Undergraduate Grade Scale', 'desc': 'Standard UG grading'},
                {'value': 'PG_SCALE', 'display': 'Postgraduate Grade Scale', 'desc': 'PG grading'},
            ],
        }

        created_values = 0
        with transaction.atomic():
            for category_name, values_list in sample_values.items():
                try:
                    category = MetadataCategory.objects.get(name=category_name)
                except MetadataCategory.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Category "{category_name}" not found, skipping values.'))
                    continue

                for val in values_list:
                    obj, created = MetadataValue.objects.get_or_create(
                        category=category,
                        value=val['value'],
                        defaults={
                            'display_name': val['display'],
                            'description': val.get('desc', ''),
                        }
                    )
                    if created:
                        created_values += 1
                        self.stdout.write(f'    + Added value: {val["display"]} for {category_name}')
                    else:
                        self.stdout.write(f'    - Value already exists: {val["display"]} for {category_name}')

        self.stdout.write(self.style.SUCCESS(f'Values: {created_values} created.'))

        self.stdout.write(self.style.SUCCESS('Metadata seeding completed successfully.'))