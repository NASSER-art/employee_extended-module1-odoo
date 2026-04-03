# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # =============================================
    # Niveau d'éducation
    # =============================================
    education_level = fields.Selection([
        ('btp', 'BTP - Brevet de Technicien Professionnel'),
        ('bts', 'BTS - Brevet de Technicien Supérieur'),
        ('cap', 'CAP - Certificat d\'Aptitude Professionnelle'),
        ('licence', 'Licence'),
        ('master', 'Master / Mastère'),
        ('ingenieur', 'Ingénieur'),
        ('doctorat', 'Doctorat'),
        ('equivalent', 'Équivalent'),
        ('other', 'Autre'),
    ], string="Niveau d'éducation", tracking=True,
       help="Niveau d'éducation selon le système éducatif tunisien")

    education_institution = fields.Char(
        string="Établissement de formation",
        help="Nom de l'établissement de formation ou université",
    )
    education_year = fields.Char(
        string="Année d'obtention",
    )
    education_speciality = fields.Char(
        string="Spécialité",
    )

    # =============================================
    # Identification
    # =============================================
    cin_number = fields.Char(
        string="Numéro CIN",
        tracking=True,
        help="Numéro de la Carte d'Identité Nationale",
        size=8,
    )
    cin_delivery_date = fields.Date(
        string="Date de délivrance CIN",
    )
    cin_delivery_place = fields.Char(
        string="Lieu de délivrance CIN",
    )
    cin_attachment = fields.Binary(
        string="Copie de la CIN",
        attachment=True,
        help="Joindre la copie scannée de la carte d'identité nationale",
    )
    cin_attachment_name = fields.Char(
        string="Nom du fichier CIN",
    )

    cnss_number = fields.Char(
        string="Numéro CNSS",
        tracking=True,
        help="Numéro d'affiliation à la Caisse Nationale de Sécurité Sociale",
    )

    @api.constrains('cin_number')
    def _check_cin_number(self):
        for emp in self:
            if emp.cin_number:
                if not emp.cin_number.isdigit() or len(emp.cin_number) != 8:
                    raise ValidationError(
                        _("Le numéro CIN doit contenir exactement 8 chiffres.")
                    )
                # Vérifier l'unicité
                duplicate = self.search([
                    ('cin_number', '=', emp.cin_number),
                    ('id', '!=', emp.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Le numéro CIN %s est déjà attribué à l'employé %s.") %
                        (emp.cin_number, duplicate.name)
                    )
