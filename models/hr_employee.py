# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Note: contract_id est un champ standard ajouté par hr_contract
    # qui pointe vers le premier contrat actif ou le plus récent.

    contract_type_extended = fields.Selection(
        related='contract_id.contract_type_extended',
        string="Type de contrat",
        readonly=False,
        store=True,
    )

    contract_state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Contract State', compute='_compute_contract_state', store=True)

    @api.depends('contract_id', 'contract_id.state')
    def _compute_contract_state(self):
        for employee in self:
            if employee.contract_id and hasattr(employee.contract_id, 'state'):
                employee.contract_state = employee.contract_id.state
            else:
                employee.contract_state = False

    contract_start_date = fields.Date(
        related='contract_id.date_start',
        string="Date de début du contrat",
        readonly=False,
        store=True,
    )
    contract_end_date = fields.Date(
        related='contract_id.date_end',
        string="Date de fin du contrat",
        readonly=False,
        store=True,
    )

    # Période d'essai
    is_trial_period = fields.Boolean(
        related='contract_id.is_trial_period',
        string="En période d'essai",
        readonly=False,
        store=True,
    )
    trial_start_date = fields.Date(
        related='contract_id.trial_date_start',
        string="Début période d'essai",
        readonly=False,
        store=True,
    )
    trial_end_date = fields.Date(
        related='contract_id.trial_date_end',
        string="Fin période d'essai",
        readonly=False,
        store=True,
    )
    trial_renewed = fields.Boolean(
        related='contract_id.trial_renewed',
        string="Période d'essai renouvelée",
        readonly=False,
        store=True,
    )
    trial_status = fields.Selection(
        related='contract_id.trial_status',
        string="Statut période d'essai",
        store=True,
    )

    # CDD spécifique
    cdd_reason = fields.Selection(
        related='contract_id.cdd_reason',
        string="Motif du CDD",
        readonly=False,
        store=True,
    )

    cdd_converted_to_cdi = fields.Boolean(
        related='contract_id.cdd_converted_to_cdi',
        string="CDD converti en CDI",
        store=True,
    )
    cdd_conversion_date = fields.Date(
        related='contract_id.cdd_conversion_date',
        string="Date de conversion CDD → CDI",
        store=True,
    )
    cdd_conversion_reason = fields.Selection(
        related='contract_id.cdd_conversion_reason',
        string="Motif de conversion",
        store=True,
    )

    contract_notes = fields.Text(
        related='contract_id.contract_notes',
        string="Notes sur le contrat",
        readonly=False,
        store=True,
    )

    def action_convert_cdd_to_cdi(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id.action_convert_cdd_to_cdi()
        return False

    def action_renew_trial(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id.action_renew_trial()
        return False

    def action_open_medical_exam_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle Fiche d\'Amplitude'),
            'res_model': 'medical.exam.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            },
        }

    fiche_aptitude_ids = fields.One2many(
        'hr.fiche.aptitude',
        'employee_id',
        string="Fiches d'aptitude",
    )

    last_fiche_aptitude_id = fields.Many2one(
        'hr.fiche.aptitude',
        string="Dernière fiche d'aptitude",
        compute="_compute_last_fiche_aptitude_id",
        store=False,
    )

    @api.depends('fiche_aptitude_ids', 'fiche_aptitude_ids.examination_date')
    def _compute_last_fiche_aptitude_id(self):
        for employee in self:
            employee.last_fiche_aptitude_id = self.env['hr.fiche.aptitude'].search(
                [('employee_id', '=', employee.id)],
                order='examination_date desc, id desc',
                limit=1,
            )

    # ====================================================================
    # OVERRIDE: Contract Warning Logic - Based on End Date, Not Status
    # ====================================================================
    @api.depends('contract_id', 'contract_id.date_end')
    def _compute_contract_warning(self):
        """
        OVERRIDE: Avertissement de contrat basé sur la date de fin
        
        Avertissement = VRAI si:
        1. L'employé n'a pas de contrat actuel
        2. La date de fin du contrat approche (dans les 30 prochains jours)
        
        Avertissement = FAUX si:
        - C'est un CDI (pas de date de fin)
        """
        for employee in self:
            if not employee.contract_id:
                # Pas de contrat actuel
                employee.contract_warning = True
            elif not employee.contract_id.date_end:
                # CDI sans date de fin - pas d'avertissement
                employee.contract_warning = False
            else:
                # Vérifier si la date de fin approche (dans les 30 prochains jours)
                days_until_end = (employee.contract_id.date_end - date.today()).days
                employee.contract_warning = days_until_end <= 30 and days_until_end > 0

    def action_view_all_fiches(self):
        """Ouvrir toutes les fiches d'aptitude de cet employé (actives ET inactives)"""
        return {
            'name': f'Fiches d\'aptitude - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.fiche.aptitude',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'active_test': False, 'search_default_group_employee': False},
        }
