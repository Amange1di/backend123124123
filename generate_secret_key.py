#!/usr/bin/env python
"""
Скрипт для генерации SECRET_KEY для Django
"""
from django.core.management.utils import get_random_secret_key

if __name__ == '__main__':
    print("Сгенерированная SECRET_KEY:")
    print(get_random_secret_key())
