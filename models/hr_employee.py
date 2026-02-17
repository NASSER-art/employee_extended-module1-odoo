# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Note: contract_id est un champ standard ajouté par hr_contract
    # qui pointe vers le premier contrat actif ou le plus récent.

    contract_type_extended = fields.Selection(
        related='contract_id.contract_type_extended',
        string="Type de contrat Tunisie",
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
