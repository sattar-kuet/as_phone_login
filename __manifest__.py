# -*- coding: utf-8 -*-
{
    'name': "Phone Login",
    'summary': """ Do login with phone number""",
    'author': "My Company",
    'category': 'website',
    'version': '1.0',
    'depends': [ 'auth_oauth', 'smart_courier','as_phone_login'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'application':True,
}
