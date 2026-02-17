# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    civil_status_extended = fields.Selection([
        ('single', 'Célibataire'),
        ('married', 'Marié(e)'),
        ('divorced', 'Divorcé(e)'),
        ('widowed', 'Veuf/Veuve'),
    ], string="État civil", tracking=True)

    chef_de_famille = fields.Boolean(
        string="Chef de famille",
        default=False,
        tracking=True,
        help="Cocher si l'employé est chef de famille",
    )
    show_chef_de_famille = fields.Boolean(
        compute='_compute_show_chef_de_famille',
    )
    nombre_enfants = fields.Integer(
        string="Nombre d'enfants",
        default=0,
    )
    conjoint_name = fields.Char(
        string="Nom du conjoint",
    )
    conjoint_employer = fields.Char(
        string="Employeur du conjoint",
    )

    @api.depends('civil_status_extended')
    def _compute_show_chef_de_famille(self):
        for emp in self:
            emp.show_chef_de_famille = emp.civil_status_extended == 'married'

    @api.onchange('civil_status_extended')
    def _onchange_civil_status(self):
        """Réinitialiser chef de famille si célibataire"""
        if self.civil_status_extended != 'married':
            self.chef_de_famille = False
            self.conjoint_name = False
            self.conjoint_employer = False

    @api.constrains('nombre_enfants')
    def _check_nombre_enfants(self):
        for emp in self:
            if emp.nombre_enfants < 0:
                raise ValidationError(
                    _("Le nombre d'enfants ne peut pas être négatif.")
                )
