#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the parent directory to the path so Django can find the project settings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sparkle.settings')
django.setup()

# Run tests
TestRunner = get_runner(settings)
test_runner = TestRunner(verbosity=2, interactive=True)

# Run only voice_assistant tests
failures = test_runner.run_tests(['voice_assistant'])

# Exit with the number of failures as the status code
sys.exit(bool(failures)) 