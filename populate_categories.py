import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Task_Wizards.settings')
django.setup()

from marketplace.models import Category

def populate():
    categories = [
        "Graphics & Design",
        "Digital Marketing",
        "Writing & Translation",
        "Video & Animation",
        "Music & Audio",
        "Programming & Tech",
        "Photography",
        "Business",
        "AI Services"
    ]

    for name in categories:
        category, created = Category.objects.get_or_create(name=name)
        if created:
            print(f"Created category: {name}")
        else:
            print(f"Category already exists: {name}")

if __name__ == "__main__":
    print("Populating categories...")
    populate()
    print("Done!")
