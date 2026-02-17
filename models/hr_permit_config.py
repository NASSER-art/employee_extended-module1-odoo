# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrPermitConfig(models.Model):
    _name = 'hr.permit.config'
    _description = 'Configuration des Alertes Permis'

    name = fields.Char(string="Nom", default="Configuration Mail", readonly=True)
    notify_before_days = fields.Integer(
        string="Alerter N jours avant",
        default=15,
        help="Nombre de jours avant l'expiration pour envoyer l'email d'alerte."
    )

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'notify_before_days': 15})
        return config
