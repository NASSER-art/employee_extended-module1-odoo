# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_trial_end_date_from_start(self, start_date, renewed=False):
        months = 12 if renewed else 6
        return start_date + relativedelta(months=months) - relativedelta(days=1)

    def _apply_cdi_trial_sync_to_vals(self, vals, is_cdi=False):
        vals = dict(vals)
        if not is_cdi:
            return vals
        if vals.get('trial_date_start'):
            vals['date_start'] = vals['trial_date_start']
        if vals.get('trial_date_end'):
            vals['date_end'] = vals['trial_date_end']
        return vals

    def _get_cdi_autofix_vals(self, force_initial_trial=False):
        self.ensure_one()
        vals = {}
        if self.contract_type_extended != 'cdi':
            return vals

        # Only sync trial dates to contract dates during initial trial period setup
        if force_initial_trial:
            if self.trial_date_start and self.date_start != self.trial_date_start:
                vals['date_start'] = self.trial_date_start
            if self.trial_date_end and self.date_end != self.trial_date_end:
                vals['date_end'] = self.trial_date_end

        if force_initial_trial and self.date_start and not self.is_trial_period:
            vals['is_trial_period'] = True

        if self.date_start and (self.is_trial_period or vals.get('is_trial_period')):
            if force_initial_trial:
                renewed = False
                expected_end = self._get_trial_end_date_from_start(self.date_start, renewed=renewed)
                if self.trial_date_start != self.date_start:
                    vals['trial_date_start'] = self.date_start
                if self.trial_date_end != expected_end:
                    vals['trial_date_end'] = expected_end
                if self.trial_renewed:
                    vals['trial_renewed'] = False
            else:
                if not self.trial_date_start:
                    vals['trial_date_start'] = self.date_start
                if not self.trial_date_end:
                    base_start = self.trial_date_start or self.date_start
                    vals['trial_date_end'] = self._get_trial_end_date_from_start(
                        base_start, renewed=bool(self.trial_renewed)
                    )
        return vals

    contract_type_extended = fields.Selection([
        ('cdi', 'CDI - Contrat à Durée Indéterminée'),
        ('cdd', 'CDD - Contrat à Durée Déterminée'),
        ('sivp', 'SIVP - Stage d\'Initiation à la Vie Professionnelle'),
        ('karma', 'Karma - Programme d\'Emploi et de Travail Décent'),
    ], string="Type de contrat",
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
            # Ne pas cocher automatiquement la période d'essai - laisser l'utilisateur le faire manuellement
            if not self.is_trial_period:
                self.trial_date_start = False
                self.trial_date_end = False
                self.trial_renewed = False
        elif self.contract_type_extended == 'cdd':
            self.is_trial_period = False
            self.trial_date_start = False
            self.trial_date_end = False
            self.trial_renewed = False

    @api.onchange('date_start', 'is_trial_period', 'trial_renewed', 'trial_date_start', 'trial_date_end')
    def _onchange_sync_cdi_trial_and_contract_dates(self):
        for contract in self:
            if contract.contract_type_extended != 'cdi':
                continue

            # Si la période d'essai est décochée, vider les dates de fin et d'essai
            if not contract.is_trial_period:
                contract.date_end = False
                contract.trial_date_start = False
                contract.trial_date_end = False
                contract.trial_renewed = False
                continue

            # Les dates d'essai ne se synchronisent que si la période d'essai est cochée
            if contract.trial_date_start and contract.is_trial_period:
                contract.date_start = contract.trial_date_start
            elif contract.is_trial_period and contract.date_start:
                contract.trial_date_start = contract.date_start

            if contract.trial_date_end and contract.is_trial_period:
                contract.date_end = contract.trial_date_end
            elif contract.is_trial_period and contract.trial_date_start:
                contract.trial_date_end = contract._get_trial_end_date_from_start(
                    contract.trial_date_start,
                    renewed=bool(contract.trial_renewed),
                )
                contract.date_end = contract.trial_date_end

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            is_cdi = vals.get('contract_type_extended') == 'cdi'
            new_vals = self._apply_cdi_trial_sync_to_vals(vals, is_cdi=is_cdi)
            normalized_vals_list.append(new_vals)

        vals_list = normalized_vals_list
        contracts = super().create(vals_list)
        for contract in contracts:
            # Only auto-fix trial dates if the user explicitly enabled trial period
            force_initial_trial = contract.contract_type_extended == 'cdi' and contract.is_trial_period
            fix_vals = contract._get_cdi_autofix_vals(force_initial_trial=force_initial_trial)
            if fix_vals:
                super(HrContract, contract).write(fix_vals)
        return contracts

    def write(self, vals):
        vals = dict(vals)
        target_is_cdi = vals.get('contract_type_extended') == 'cdi' or any(c.contract_type_extended == 'cdi' for c in self)
        vals = self._apply_cdi_trial_sync_to_vals(vals, is_cdi=target_is_cdi)

        res = super().write(vals)
        for contract in self:
            # Only auto-fix trial dates if the user explicitly enables is_trial_period
            force_initial_trial = (
                'is_trial_period' in vals
                and vals['is_trial_period'] is True
                and contract.contract_type_extended == 'cdi'
            )
            fix_vals = contract._get_cdi_autofix_vals(force_initial_trial=force_initial_trial)
            if fix_vals:
                super(HrContract, contract).write(fix_vals)
        return res

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
            # Only validate if record is already saved in database (has an id)
            if not contract.id:
                continue
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
                'cdd_reason': False,
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
