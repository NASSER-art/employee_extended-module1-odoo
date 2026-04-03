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
    driving_permit_category = fields.Selection(
        related='employee_id.driving_permit_category',
        string="Catégorie du permis",
        store=True,
    )
    permis_end_date = fields.Date(
        related='employee_id.permis_end_date',
        string="Date de fin du permis",
        store=True,
    )
    days_remaining = fields.Integer(
        string="Jours restants",
        store=True,
        help="Nombre de jours avant expiration (calculé lors de la dernière vérification)"
    )
    state = fields.Selection([
        ('valid', 'Valide'),
        ('warning', 'Attention'),
        ('critical', 'Critique'),
        ('expired', 'Expiré'),
        ('na', 'N/A'),
    ], string="État",
        store=True,
    )
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

    def action_resend_alert(self):
        """Réinitialiser l'alerte pour forcer un renvoi automatique au prochain cron"""
        for record in self:
            record.alert_sent = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Alerte réinitialisée",
                'message': "L'email d'alerte sera renvoyé au prochain cron job (24h max)",
                'type': 'success',
                'sticky': False,
            }
        }

