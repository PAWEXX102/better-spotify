#!/bin/bash
pip install setuptools
pip install -r requirements.txt

python manage.py makemigratoins
python manage.py migrate
python manage.py collectstatic