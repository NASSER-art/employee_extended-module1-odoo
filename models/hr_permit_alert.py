# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class HrPermitAlert(models.Model):
    """Modèle pour le suivi des alertes de permis"""
    _name = 'hr.permit.alert'
    _description = "Alerte d'expiration de permis de conduire"
    _order = 'permis_end_date asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Référence",
        compute='_compute_name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employé",
        required=True,
        ondelete='cascade',
    )
    employee_name = fields.Char(
        related='employee_id.name',
        string="Nom de l'employé",
        store=True,
    )
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string="Département",
        store=True,
    )
    permis_end_date = fields.Date(
        related='employee_id.permis_end_date',
        string="Date de fin du permis",
        store=True,
    )
    days_remaining = fields.Integer(
        string="Jours restants",
        compute='_compute_days_remaining',
        store=True,
    )
    state = fields.Selection([
        ('valid', 'Valide'),
        ('warning', 'Attention (< 30 jours)'),
        ('critical', 'Critique (< 15 jours)'),
        ('expired', 'Expiré'),
    ], string="État", compute='_compute_state', store=True)
    alert_sent = fields.Boolean(string="Alerte envoyée", default=False)
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
    )

    @api.depends('employee_id', 'permis_end_date')
    def _compute_name(self):
        for record in self:
            if record.employee_id and record.permis_end_date:
                record.name = f"PERMIS-{record.employee_id.name}-{record.permis_end_date}"
            else:
                record.name = "Nouveau"

    @api.depends('permis_end_date')
    def _compute_days_remaining(self):
        today = date.today()
        for record in self:
            if record.permis_end_date:
                delta = record.permis_end_date - today
                record.days_remaining = delta.days
            else:
                record.days_remaining = 0

    @api.depends('days_remaining')
    def _compute_state(self):
        for record in self:
            if record.days_remaining <= 0:
                record.state = 'expired'
            elif record.days_remaining <= 15:
                record.state = 'critical'
            elif record.days_remaining <= 30:
                record.state = 'warning'
            else:
                record.state = 'valid'
