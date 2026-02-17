# -*- coding: utf-8 -*-
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class HrContract(models.Model):
    _inherit = 'hr.contract'

    contract_type_extended = fields.Selection([
        ('cdi', 'CDI - Contrat à Durée Indéterminée'),
        ('cdd', 'CDD - Contrat à Durée Déterminée'),
        ('sivp', 'SIVP - Stage d\'Initiation à la Vie Professionnelle'),
        ('karma', 'Karma - Programme d\'Emploi et de Travail Décent'),
    ], string="Type de contrat Tunisie",
       default='cdi',
       tracking=True,
       help="CDI par défaut sauf exceptions légales. SIVP et Karma sont des programmes tunisiens.")

    # CDD spécifique
    cdd_reason = fields.Selection([
        ('temporary_increase', "Surcroît temporaire d'activité"),
        ('temporary_replacement', 'Remplacement provisoire'),
        ('seasonal_work', 'Travaux saisonniers'),
        ('specific_project', 'Projet spécifique'),
    ], string="Motif du CDD",
       help="Le CDD est uniquement autorisé pour ces cas exceptionnels")

    # CDI Période d'essai
    is_trial_period = fields.Boolean(
        string="En période d'essai",
        default=False,
    )
    trial_renewed = fields.Boolean(
        string="Période d'essai renouvelée",
        default=False,
    )
    trial_date_start = fields.Date(
        string="Début période d'essai",
    )
    trial_status = fields.Selection([
        ('in_progress', 'En cours'),
        ('renewed', 'Renouvelée'),
        ('completed', 'Terminée'),
        ('terminated', 'Rompue'),
    ], string="Statut période d'essai",
       compute='_compute_trial_status',
       store=True,
    )

    cdd_converted_to_cdi = fields.Boolean(
        string="CDD converti en CDI",
        default=False,
        tracking=True,
    )
    cdd_conversion_date = fields.Date(
        string="Date de conversion CDD → CDI",
    )
    cdd_conversion_reason = fields.Selection([
        ('non_compliant', 'CDD non conforme'),
        ('continued_after_end', 'Continuation après fin du CDD'),
        ('manual', 'Conversion manuelle'),
    ], string="Motif de conversion")

    contract_notes = fields.Text(
        string="Notes sur le contrat (Tunisie)",
    )

    @api.depends('trial_date_start', 'trial_date_end', 'trial_renewed',
                 'contract_type_extended', 'is_trial_period')
    def _compute_trial_status(self):
        today = date.today()
        for contract in self:
            if contract.contract_type_extended != 'cdi' or not contract.is_trial_period:
                contract.trial_status = False
            elif not contract.trial_date_end:
                contract.trial_status = 'in_progress'
            elif today > contract.trial_date_end:
                contract.trial_status = 'completed'
            elif contract.trial_renewed:
                contract.trial_status = 'renewed'
            else:
                contract.trial_status = 'in_progress'

    @api.onchange('contract_type_extended')
    def _onchange_contract_type_extended(self):
        if self.contract_type_extended == 'cdi':
            self.cdd_reason = False
            self.date_end = False
        elif self.contract_type_extended == 'cdd':
            self.is_trial_period = False
            self.trial_date_start = False
            self.trial_date_end = False
            self.trial_renewed = False

    @api.constrains('trial_date_start', 'trial_date_end', 'trial_renewed')
    def _check_trial_period_tunisia(self):
        for contract in self:
            if contract.contract_type_extended == 'cdi' and contract.is_trial_period:
                if contract.trial_date_start and contract.trial_date_end:
                    if contract.trial_date_end <= contract.trial_date_start:
                        raise ValidationError(_("La date de fin de période d'essai doit être postérieure à la date de début."))
                    delta = relativedelta(contract.trial_date_end, contract.trial_date_start)
                    total_months = delta.years * 12 + delta.months
                    if delta.days > 0:
                        total_months += 1
                    max_months = 12 if contract.trial_renewed else 6
                    if total_months > max_months:
                        if contract.trial_renewed:
                            raise ValidationError(_("La période d'essai totale ne peut excéder 12 mois (6 mois + 1 renouvellement de 6 mois)."))
                        else:
                            raise ValidationError(_("La période d'essai initiale ne peut excéder 6 mois. Vous pouvez la renouveler une fois."))

    @api.constrains('contract_type_extended', 'cdd_reason')
    def _check_cdd_reason(self):
        for contract in self:
            if contract.contract_type_extended == 'cdd' and not contract.cdd_reason:
                raise ValidationError(_("Un CDD doit obligatoirement avoir un motif."))

    @api.constrains('contract_type_extended', 'date_start', 'date_end')
    def _check_contract_dates_tunisia(self):
        for contract in self:
            if contract.contract_type_extended == 'cdd':
                if contract.date_start and contract.date_end:
                    if contract.date_end <= contract.date_start:
                        raise ValidationError(_("La date de fin du CDD doit être postérieure à la date de début."))

    def action_convert_cdd_to_cdi(self):
        for contract in self:
            if contract.contract_type_extended != 'cdd':
                raise UserError(_("Seul un CDD peut être converti en CDI."))
            contract.write({
                'contract_type_extended': 'cdi',
                'cdd_converted_to_cdi': True,
                'cdd_conversion_date': date.today(),
                'cdd_conversion_reason': 'manual',
                'date_end': False,
                'cdd_reason': False,
            })
            contract.message_post(body=_("Le contrat CDD a été converti en CDI le %s.") % date.today())
            if contract.employee_id:
                contract.employee_id.message_post(body=_("Le contrat de l'employé a été converti en CDI."))

    def action_renew_trial(self):
        for contract in self:
            if contract.contract_type_extended != 'cdi':
                raise UserError(_("La période d'essai n'est applicable qu'aux CDI."))
            if contract.trial_renewed:
                raise UserError(_("La période d'essai a déjà été renouvelée."))
            if not contract.trial_date_end:
                raise UserError(_("Veuillez d'abord définir la date de fin de la période d'essai initiale."))
            new_end = contract.trial_date_end + relativedelta(months=6)
            contract.write({
                'trial_renewed': True,
                'trial_date_end': new_end,
            })
            contract.message_post(body=_("La période d'essai a été renouvelée jusqu'au %s.") % new_end)

    @api.model
    def _cron_check_cdd_expiry_tunisia(self):
        today = date.today()
        contracts_cdd_expired = self.search([
            ('state', '=', 'open'),
            ('contract_type_extended', '=', 'cdd'),
            ('date_end', '!=', False),
            ('date_end', '<', today),
            ('cdd_converted_to_cdi', '=', False),
        ])
        for contract in contracts_cdd_expired:
            prev_end = contract.date_end
            contract.write({
                'contract_type_extended': 'cdi',
                'cdd_converted_to_cdi': True,
                'cdd_conversion_date': today,
                'cdd_conversion_reason': 'continued_after_end',
                'date_end': False,
            })
            body = _("🔄 <b>CONVERSION AUTOMATIQUE CDD → CDI</b> : Le CDD de ce contrat a pris fin le %s.") % prev_end
            contract.message_post(body=body)
            if contract.employee_id:
                contract.employee_id.message_post(body=body)
                hr_managers = self.env.ref('hr.group_hr_manager').users
                for manager in hr_managers:
                    contract.employee_id.activity_schedule('mail.mail_activity_data_todo', user_id=manager.id, note=_("Le contrat de %s a été automatiquement converti en CDI.") % contract.employee_id.name)
        return True

    @api.model
    def _cron_check_trial_period_tunisia(self):
        today = date.today()
        contracts_trial_ended = self.search([
            ('state', '=', 'open'),
            ('contract_type_extended', '=', 'cdi'),
            ('is_trial_period', '=', True),
            ('trial_date_end', '!=', False),
            ('trial_date_end', '<', today),
        ])
        for contract in contracts_trial_ended:
            contract.write({'is_trial_period': False})
            body = _("✅ <b>PÉRIODE D'ESSAI TERMINÉE</b> : La période d'essai de ce contrat s'est terminée le %s.") % contract.trial_date_end
            contract.message_post(body=body)
            if contract.employee_id:
                contract.employee_id.message_post(body=body)
        return True
