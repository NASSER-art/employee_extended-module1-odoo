# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_driving_permit = fields.Boolean(
        string="Possède un permis de conduire",
        default=False,
    )
    send_permit_alert_mail = fields.Boolean(
        string="Envoyer alerte mail",
        default=True,
        help="Si coché, une alerte par email sera envoyée avant l'expiration.",
    )
    send_permit_alert_to_manager = fields.Boolean(
        string="Avertir le manager par mail",
        default=False,
        help="Si coché, le manager recevra également l'alerte par email.",
    )
    driving_permit_number = fields.Char(
        string="Numéro du permis",
        tracking=True,
    )
    driving_permit_category = fields.Selection([
        ('a1', 'A1 - Motocyclette légère'),
        ('a', 'A - Motocyclette'),
        ('b', 'B - Véhicule léger'),
        ('c', 'C - Poids lourd'),
        ('d', 'D - Transport en commun'),
        ('e', 'E - Remorque'),
    ], string="Catégorie du permis")

    permis_end_date = fields.Date(
        string="Date de fin du permis",
        tracking=True,
        help="Date d'expiration du permis de conduire",
    )
    permis_days_remaining = fields.Integer(
        string="Jours restants (permis)",
        compute='_compute_permis_days_remaining',
        store=True,
    )
    permis_status = fields.Selection([
        ('valid', 'Valide'),
        ('warning', 'Attention'),
        ('critical', 'Critique'),
        ('expired', 'Expiré'),
        ('na', 'N/A'),
    ], string="Statut du permis",
       compute='_compute_permis_status',
       store=True,
    )
    permis_attachment = fields.Binary(
        string="Copie du permis",
        attachment=True,
    )
    permis_attachment_name = fields.Char(
        string="Nom du fichier permis",
    )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super(HrEmployee, self).create(vals_list)
        for emp in employees:
            if emp.has_driving_permit and emp.permis_end_date:
                emp._update_permit_alert_record()
        return employees

    def write(self, vals):
        res = super(HrEmployee, self).write(vals)
        fields_to_check = ['permis_end_date', 'has_driving_permit', 'send_permit_alert_mail']
        if any(field in vals for field in fields_to_check):
            for emp in self:
                emp._update_permit_alert_record()
        return res

    @api.depends('permis_end_date')
    def _compute_permis_days_remaining(self):
        today = date.today()
        for emp in self:
            if emp.permis_end_date:
                delta = emp.permis_end_date - today
                emp.permis_days_remaining = delta.days
            else:
                emp.permis_days_remaining = 0

    @api.depends('permis_days_remaining', 'has_driving_permit')
    def _compute_permis_status(self):
        for emp in self:
            if not emp.has_driving_permit or not emp.permis_end_date:
                emp.permis_status = 'na'
            elif emp.permis_days_remaining <= 0:
                emp.permis_status = 'expired'
            elif emp.permis_days_remaining <= 15:
                emp.permis_status = 'critical'
            elif emp.permis_days_remaining <= 30:
                emp.permis_status = 'warning'
            else:
                emp.permis_status = 'valid'

    @api.onchange('has_driving_permit')
    def _onchange_has_driving_permit(self):
        if not self.has_driving_permit:
            self.driving_permit_number = False
            self.driving_permit_category = False
            self.permis_end_date = False

    @api.model
    def _cron_check_permit_expiry(self):
        """Tâche planifiée pour vérifier les permis"""
        employees = self.search([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
        ])
        for emp in employees:
            emp._update_permit_alert_record()
        return True

    def _update_permit_alert_record(self):
        """Crée ou met à jour l'enregistrement d'alerte pour cet employé"""
        self.ensure_one()
        AlertModel = self.env['hr.permit.alert']
        existing_alerts = AlertModel.search([('employee_id', '=', self.id)])
        
        # Handle duplicates: keep one, delete others
        if len(existing_alerts) > 1:
            # Prefer the one that already sent an alert, or the most recently created one
            details = []
            for alert in existing_alerts:
                details.append((alert.alert_sent, alert.create_date, alert.id, alert))
            
            # Sort: alert_sent DESC (True first), create_date DESC (newest first)
            details.sort(key=lambda x: (x[0], x[1]), reverse=True)
            
            existing_alert = details[0][3]
            # Unlink the rest
            for i in range(1, len(details)):
                details[i][3].unlink()
        else:
            existing_alert = existing_alerts

        if not self.has_driving_permit or not self.permis_end_date or not self.send_permit_alert_mail:
            if existing_alert:
                existing_alert.unlink()
            return

        today = date.today()
        warning_date = today + timedelta(days=30)
        
        if self.permis_end_date > warning_date:
            if existing_alert:
                existing_alert.unlink()
            return

        if not existing_alert:
            existing_alert = AlertModel.create({'employee_id': self.id})

        days_remaining = (self.permis_end_date - today).days
        config = self.env['hr.permit.config'].sudo().get_config()
        trigger_days = config.notify_before_days

        if days_remaining <= trigger_days and not existing_alert.alert_sent:
            hr_managers = self.env.ref('hr.group_hr_manager', raise_if_not_found=False).users
            template = self.env.ref('employee_extended.email_template_permit_expiry', raise_if_not_found=False)
            if template:
                recipients_list = []
                if self.work_email:
                    recipients_list.append(self.work_email)
                if self.send_permit_alert_to_manager and self.parent_id and self.parent_id.work_email:
                    recipients_list.append(self.parent_id.work_email)
                if not recipients_list and hr_managers:
                    recipients_list = hr_managers.filtered(lambda u: u.email).mapped('email')
                
                if recipients_list:
                    email_to = ",".join(recipients_list)
                    try:
                        template.send_mail(self.id, email_values={'email_to': email_to}, force_send=True)
                        # Activité planifiée supprimée suite à la demande utilisateur (Step 39)
                        
                        existing_alert.write({'alert_sent': True})
                        body_prefix = _("🚨 <b>PERMIS EXPIRÉ</b>") if days_remaining <= 0 else \
                                      _("⚠️ <b>ALERTE PERMIS</b> (%d jours restants)") % days_remaining
                        self.message_post(body=body_prefix + _(": Expire le %s. Email d'alerte envoyé à %s.") % (self.permis_end_date, email_to))
                    except Exception as e:
                        _logger.error("❌ [PERMIS] Erreur lors de l'envoi du mail pour %s : %s", self.name, e)
                        self.message_post(body=_("❌ <b>Erreur mail</b> : Impossible d'envoyer l'alerte permis par e-mail (%s).") % e)
                else:
                    self.message_post(body=_("⚠️ <b>Alerte mail échouée</b> : Aucune adresse email configurée."))

    @api.model
    def get_permit_alerts_count(self):
        """Retourne le nombre d'alertes de permis pour le widget JS"""
        today = date.today()
        warning_date = today + timedelta(days=30)
        return self.search_count([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
            ('permis_end_date', '<=', warning_date),
        ])

    @api.model
    def get_permit_alerts_data(self):
        """Retourne les données des alertes de permis pour le widget JS"""
        today = date.today()
        warning_date = today + timedelta(days=30)
        employees = self.search([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
            ('permis_end_date', '<=', warning_date),
        ])
        alerts = []
        for emp in employees:
            days = (emp.permis_end_date - today).days
            alerts.append({
                'id': emp.id,
                'name': emp.name,
                'end_date': str(emp.permis_end_date),
                'days_remaining': days,
                'status': 'expired' if days <= 0 else ('critical' if days <= 15 else 'warning'),
            })
        return alerts

    def action_view_permit_status(self):
        """Action appelée depuis le stat button pour voir le détail du permis"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Statut du permis - %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': {'default_page': 'page_permit'},
        }
