# Library Service 

Online management system for book borrowings.

## Features

* JWT authenticated.
* Admin panel /admin/
* Documentation at /api/doc/swagger/
* Books inventory management.
* Books borrowing management.
* Notifications service through Telegram API (bot and chat).
* Scheduled notifications with Django Q and Redis.
* Payments handle with Stripe API.

## Installation
Python3 must be already installed

1. Clone project and create virtual environment
```shell
git clone https://github.com/arsenmakovei/library-service.git
cd library_service
python -m venv venv
Windows: venv\Scripts\activate
Linux, Unix: source venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables

On Windows use ```export``` command instead of ```set```
```shell
set SECRET_KEY=<your Django secret key>
set STRIPE_API_KEY=<your Stripe API key>
set TELEGRAM_BOT_TOKEN=<your Telegram Bot token>
set TELEGRAM_CHAT_ID=<your Telegram chat id>
```

3. Make migrations and run server
```shell
python manage.py migrate
python manage.py runserver
```

4. Getting daily scheduled notifications in Telegram

* start Redis server
* create admin using `python manage.py createsuperuser`
* create a task by following the link http://127.0.0.1:8000/admin/django_q/schedule/
* run `python manage.py qcluster`

## Getting access

* create user via /api/users/
* get access token via /api/users/token/