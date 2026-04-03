# -*- coding: utf-8 -*-

{
    'name': 'extension employee moderne-metale',
    'version': '16.0.2.1.0',
    'category': 'Human Resources',
    'summary': 'Extension du module RH avec département, éducation, permis, statut social et contrat',
    'description': """
Module d'extension RH pour le contexte tunisien:
- Département et sous-département d'affectation
- Niveau d'éducation (BTP, BTS, CAP, Équivalent)
- Gestion du permis de conduire avec alertes d'expiration
- Informations sociales (CIN, chef de famille)
- Gestion des types de contrat CDI/CDD avec règles légales tunisiennes
- Conversion automatique CDD vers CDI
- Alertes et notifications automatiques
    """,
    'author': 'Nasser Letaif',
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
        'security/medical_exam_type_security.xml',
        'data/cron_data.xml',
        'data/mail_data.xml',
        'data/medical_exam_types.xml',
        'views/medical_exam_type_views.xml',
        'views/hr_fiche_aptitude_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_education_views.xml',
        'views/hr_employee_social_views.xml',
        'views/hr_employee_permit_views.xml',
        'views/hr_employee_contract_views.xml',
        'views/hr_employee_amplitude_views.xml',
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
