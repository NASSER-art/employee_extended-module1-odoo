# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MedicalExamType(models.Model):
    """Medical exam type configuration"""
    _name = 'medical.exam.type'
    _description = 'Type of Medical Examination'
    _order = 'name asc'

    name = fields.Char(
        string="Nom du type d'examen",
        required=True,
        help="Name of the medical exam type (e.g., Périodique, Reprise, etc.)"
    )

    code = fields.Char(
        string="Code",
        help="Unique code for the exam type (e.g., PER, REP, AVR, SPO, EMB)",
        index=True,
    )

    validity_days = fields.Integer(
        string="Durée de validité (jours)",
        help="Default validity duration in days from examination date"
    )

    description = fields.Text(
        string="Description",
        help="Explanation and details about this exam type"
    )

    active = fields.Boolean(
        string="Actif",
        default=True,
        help="If unchecked, this exam type will not be available for selection"
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', _('The code must be unique!')),
    ]

    def __str__(self):
        return self.name

    def action_open_medical_exam_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Nouvelle Fiche d'Amplitude"),
            'res_model': 'medical.exam.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_exam_type_id': self.id,
            },
        }
