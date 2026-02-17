# -*- coding: utf-8 -*-

{
    'name': 'Employee Extended - RH Tunisie',
    'version': '16.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Extension du module RH avec département, éducation, permis, statut social et contrat',
    'description': """
Module d'extension RH pour le contexte tunisien:
- Département et sous-département d'affectation
- Niveau d'éducation (BTP, BTS, CAP, Équivalent)
- Gestion du permis de conduire avec alertes d'expiration
- Informations sociales (état civil, CIN, chef de famille)
- Gestion des types de contrat CDI/CDD avec règles légales tunisiennes
- Conversion automatique CDD vers CDI
- Alertes et notifications automatiques
    """,
    'author': 'Custom Development',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_contract',
        'mail',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'data/mail_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_permit_config_views.xml',
        'views/permit_alert_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_extended/static/src/js/permit_notification.js',
            'employee_extended/static/src/xml/permit_notification.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
