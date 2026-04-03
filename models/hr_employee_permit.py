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
        help=' saisie le numero de permis de conduire'
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
        store=False,
    )
    permis_status = fields.Selection([
        ('valid', 'Valide'),
        ('warning', 'Attention'),
        ('critical', 'Critique'),
        ('expired', 'Expiré'),
        ('na', 'N/A'),
    ], string="Statut du permis",
       compute='_compute_permis_status',
       store=False,
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

        # ✅ FIX 1 : Si la date change → reset alert_sent pour permettre un nouvel envoi
        if 'permis_end_date' in vals:
            AlertModel = self.env['hr.permit.alert']
            for emp in self:
                alerts = AlertModel.search([('employee_id', '=', emp.id)])
                if alerts:
                    alerts.write({'alert_sent': False})

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
        # ✅ FIX 2 : Utiliser notify_before_days au lieu de 15/30 codés en dur
        config = self.env['hr.permit.config'].sudo().get_config()
        n = config.notify_before_days or 30
        half_n = n // 2  # Point intermédiaire
        
        _logger.debug("📊 [PERMIS STATUS] Calcul des statuts - n=%d, half_n=%d", n, half_n)
        
        for emp in self:
            if not emp.has_driving_permit or not emp.permis_end_date:
                emp.permis_status = 'na'
            elif emp.permis_days_remaining <= 0:
                emp.permis_status = 'expired'
                _logger.warning("🚨 [PERMIS] %s EXPIRÉ (jours_restants=%d)", emp.name, emp.permis_days_remaining)
            elif emp.permis_days_remaining <= half_n:
                emp.permis_status = 'critical'
                _logger.warning("⚠️ [PERMIS] %s CRITIQUE (jours_restants=%d, config=%d)", emp.name, emp.permis_days_remaining, n)
            elif emp.permis_days_remaining <= n:
                emp.permis_status = 'warning'
                _logger.info("ℹ️ [PERMIS] %s WARNING (jours_restants=%d, config=%d)", emp.name, emp.permis_days_remaining, n)
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
        # ✅ FIX 3 : Filtrer avec notify_before_days au lieu de tout charger
        config = self.env['hr.permit.config'].sudo().get_config()
        n = config.notify_before_days or 30
        today = date.today()
        limit_date = today + timedelta(days=n)

        _logger.info("🔄 [PERMIS CRON] ========== DÉBUT VÉRIFICATION PERMIS ==========")
        _logger.info("🔄 [PERMIS CRON] Date du jour: %s", today)
        _logger.info("🔄 [PERMIS CRON] Configuration: alerter %d jours avant expiration", n)
        _logger.info("🔄 [PERMIS CRON] Date limite: %s", limit_date)

        # ✅ FIX 4 : Tous les employés avec permis pour synchronisation totale (Beth Evans etc.)
        employees = self.search([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
            ('send_permit_alert_mail', '=', True),
        ])

        _logger.info("🔄 [PERMIS CRON] %d employé(s) à synchroniser", len(employees))

        for emp in employees:
            _logger.info("  → Processing: %s (expiration: %s, jours_restants: %d)", 
                        emp.name, emp.permis_end_date, emp.permis_days_remaining)
            emp._update_permit_alert_record()
        
        _logger.info("🔄 [PERMIS CRON] ========== FIX VÉRIFICATION PERMIS ==========")
        return True

    def _update_permit_alert_record(self):
        """
        Synchronise les données du permis vers le modèle d'alerte (hr.permit.alert)
        et déclenche l'envoi d'email si nécessaire.
        """
        self.ensure_one()
        if not self.has_driving_permit or not self.permis_end_date or not self.send_permit_alert_mail:
            return

        # 1. Synchronisation systématique pour affichage UI (Beth Evans etc.)
        AlertModel = self.env['hr.permit.alert']
        alert = AlertModel.search([('employee_id', '=', self.id)], limit=1)
        
        vals = {
            'employee_id': self.id,
            'permis_end_date': self.permis_end_date,
            'days_remaining': self.permis_days_remaining,
            'state': self.permis_status,
        }
        
        if not alert:
            alert = AlertModel.create(vals)
            _logger.info("  ✨ [PERMIS] Nouvelle alerte créée pour %s", self.name)
        else:
            alert.write(vals)
            _logger.debug("  🔄 [PERMIS] Alerte mise à jour pour %s", self.name)

        # 2. Logique d'envoi d'email d'alerte
        days_remaining = self.permis_days_remaining
        config = self.env['hr.permit.config'].sudo().get_config()
        alert_threshold = config.notify_before_days or 30

        if days_remaining <= alert_threshold:
            if not alert.alert_sent:
                _logger.info("  🔴 %s: SEUIL ATTEINT (%d <= %d) -> Envoi email", 
                             self.name, days_remaining, alert_threshold)
                self._send_alert_email(days_remaining)
            else:
                _logger.debug("  ⏭️ %s: Email déjà envoyé", self.name)
        else:
            _logger.debug("  🛡️ %s: En dehors de la zone d'alerte (> %d)", self.name, alert_threshold)
    
    def _send_alert_email(self, days_remaining):
        """Envoie un email d'alerte directement (sans template QWeb) pour éviter les erreurs de rendu."""

        # Collecter les destinataires
        recipients_list = []
        if self.work_email:
            recipients_list.append(self.work_email)
        if self.send_permit_alert_to_manager and self.parent_id and self.parent_id.work_email:
            recipients_list.append(self.parent_id.work_email)
        if not recipients_list:
            hr_managers = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if hr_managers:
                recipients_list = hr_managers.users.filtered(lambda u: u.email).mapped('email')
        if not recipients_list:
            _logger.warning("  ⚠️ AUCUN EMAIL CONFIGURÉ pour %s", self.name)
            return

        email_to = ",".join(recipients_list)
        expiry_str = str(self.permis_end_date) if self.permis_end_date else 'N/A'
        dept = self.department_id.name if self.department_id else 'N/A'
        status_label = "EXPIRÉ" if days_remaining <= 0 else f"expire dans {days_remaining} jour(s)"

        body_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h3 style="color: #e67e22;">⚠️ Alerte Expiration Permis de Conduire</h3>
            <p>Bonjour,</p>
            <p>Ceci est une alerte automatique concernant le permis de conduire de l'employé suivant :</p>
            <ul>
                <li><strong>Employé :</strong> {self.name}</li>
                <li><strong>Département :</strong> {dept}</li>
                <li><strong>Date d'expiration :</strong> {expiry_str}</li>
                <li><strong>Statut :</strong> {status_label}</li>
            </ul>
            <p>Merci de prendre les mesures nécessaires.</p>
            <p>Cordialement,<br/>Système GRH</p>
        </div>
        """

        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': f"⚠️ Alerte Expiration Permis - {self.name}",
                'email_from': "Moderne Metale RH <nasserletaif4@gmail.com>",
                'email_to': email_to,
                'body_html': body_html,
                'auto_delete': True,
            })
            mail.send()
            _logger.info("  ✅ EMAIL ENVOYÉ à %s pour %s (jours=%d)", email_to, self.name, days_remaining)

            # Marquer l'alerte comme envoyée
            AlertModel = self.env['hr.permit.alert']
            alert = AlertModel.search([('employee_id', '=', self.id)], limit=1)
            if alert:
                alert.write({'alert_sent': True})
            else:
                AlertModel.create({'employee_id': self.id, 'alert_sent': True})
            _logger.info("  ✅ alert_sent=TRUE pour %s", self.name)

        except Exception as e:
            _logger.error("  ❌ ERREUR EMAIL pour %s: %s", self.name, str(e))

    @api.model
    def get_permit_alerts_count(self):
        """Retourne le nombre d'alertes de permis pour le widget JS"""
        # ✅ FIX 8 : Dynamique au lieu de 30
        config = self.env['hr.permit.config'].sudo().get_config()
        n = config.notify_before_days or 30
        today = date.today()
        warning_date = today + timedelta(days=n)
        return self.search_count([
            ('has_driving_permit', '=', True),
            ('permis_end_date', '!=', False),
            ('permis_end_date', '<=', warning_date),
        ])

    @api.model
    def get_permit_alerts_data(self):
        """Retourne les données des alertes de permis pour le widget JS"""
        # ✅ FIX 9 : Dynamique au lieu de 30
        config = self.env['hr.permit.config'].sudo().get_config()
        n = config.notify_before_days or 30
        half_n = n // 2
        today = date.today()
        warning_date = today + timedelta(days=n)
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
                'status': 'expired' if days <= 0 else ('critical' if days <= half_n else 'warning'),
            })
        alerts.sort(key=lambda x: x['days_remaining'])
        return alerts

    def action_view_permit_status(self):
        """Action appelée depuis le stat button pour voir le détail du permis"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Détails du permis - %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }