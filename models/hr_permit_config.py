# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class HrPermitConfig(models.Model):
    _name = 'hr.permit.config'
    _description = 'Configuration des Alertes Permis'

    name = fields.Char(string="Nom", default="Configuration Mail", readonly=True)
    notify_before_days = fields.Integer(
        string="Alerter N jours avant",
        help="Nombre de jours avant l'expiration pour envoyer l'email d'alerte."
    )

    def write(self, vals):
        res = super(HrPermitConfig, self).write(vals)
        if 'notify_before_days' in vals:
            self._trigger_permit_alerts_reevaluation()
        return res

    def _trigger_permit_alerts_reevaluation(self):
        """
        Quand notify_before_days change:
        - Créer/mettre à jour les alertes en base de données
        - NE PAS renvoyer d'emails (seulement au cron job!)
        """
        n = self.notify_before_days or 30
        today = date.today()
        limit_date = today + timedelta(days=n)

        _logger.info(
            "🔄 [PERMIS CONFIG] Config changée à %d jours - Création des alertes en base", n
        )

        AlertModel = self.env['hr.permit.alert'].sudo()
        Employee = self.env['hr.employee'].sudo()

        # Chercher les employés éligibles
        employees = Employee.search([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
            ('permis_end_date', '<=', limit_date),
            ('send_permit_alert_mail', '=', True),
        ])

        _logger.info("🔄 [PERMIS CONFIG] %d employés éligibles", len(employees))

        # Créer/mettre à jour les alertes en base (SANS ENVOYER D'EMAILS)
        for emp in employees:
            alert = AlertModel.search([('employee_id', '=', emp.id)], limit=1)
            if not alert:
                alert = AlertModel.create({'employee_id': emp.id})
                _logger.info("  ✓ Alerte créée pour %s", emp.name)
            else:
                _logger.info("  ✓ Alerte existante pour %s (pas d'email renenvoyé)", emp.name)

    @api.model
    def get_config(self):
        # We take the most recent one if multiple exist (failsafe)
        config = self.search([], limit=1, order='id desc')
        if not config:
            config = self.create({})
        return config

    def action_check_permit_expiry_manual(self):
        """Action pour déclencher manuellement la vérification des permis (utile pour tests)"""
        _logger.info("🚀 [PERMIS MANUAL] Déclenchement manuel de la vérification des permis par l'admin")
        self.env['hr.employee']._cron_check_permit_expiry()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Vérification lancée ✅",
                'message': "Les permis ont été vérifiés et les alertes ont été traitées. Consultez les logs pour les détails.",
                'type': 'success',
                'sticky': False,
            }
        }
