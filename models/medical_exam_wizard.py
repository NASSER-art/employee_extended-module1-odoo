# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta


class MedicalExamWizard(models.TransientModel):
    """Wizard to capture a fiche d'aptitude au travail"""
    _name = 'medical.exam.wizard'
    _description = "Fiche d'aptitude au travail (Wizard)"

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employé",
        required=True,
    )

    exam_type_id = fields.Many2one(
        'medical.exam.type',
        string="Type d'examen",
        required=True,
        help="Type of medical examination",
    )

    exam_type_code = fields.Char(
        related='exam_type_id.code',
        string="Code statut",
        readonly=True,
    )

    validity_days = fields.Integer(
        related='exam_type_id.validity_days',
        string="Durée (jours)",
        readonly=True,
    )

    validity_months = fields.Integer(
        string="Nb. mois",
        compute="_compute_validity_breakdown",
        readonly=True,
    )

    validity_extra_days = fields.Integer(
        string="Nb. jours",
        compute="_compute_validity_breakdown",
        readonly=True,
    )

    examination_date = fields.Date(
        string="Date de l'examen",
        default=fields.Date.today,
        required=True,
    )

    expiry_date = fields.Date(
        string="Date d'expiration",
        readonly=True,
        help="Auto-calculated based on exam type validity",
    )

    fiche_status = fields.Selection([
        ('periodique', 'Périodique'),
        ('reprise', 'Reprise'),
        ('avant_reprise', 'Avant reprise'),
        ('spontane', 'Spontanée'),
        ('embauche', 'Embauche'),
    ], string="Statut de la fiche",
       compute='_compute_fiche_status',
       store=False,
    )

    aptitude_result = fields.Selection(
        [
            ('apte_poste', 'Apte au poste'),
            ('apte_amenagement', "Apte avec aménagement du poste"),
            ('inapte_temp', 'Inapte temporairement au poste'),
            ('apte_changement', "Apte après changement du poste"),
            ('inapte_def', "Inapte définitif à tout poste"),
        ],
        string="Conclusion d'aptitude",
    )

    aptitude_details = fields.Text(
        string="Précisions / recommandations",
    )

    doctor_name = fields.Char(
        string="Nom du médecin",
        help="Nom du médecin ou du médecin du travail",
    )

    medical_center = fields.Char(
        string="Centre médical",
        help="Nom ou adresse du centre médical",
    )

    restrictions = fields.Text(
        string="Restrictions de travail",
        help="Contraintes ou restrictions sur le type de travail",
    )

    notes = fields.Text(
        string="Notes du médecin",
        help="Observations et remarques médicales",
    )

    document = fields.Binary(
        string="Document de la fiche",
        attachment=True,
        help="Fichier PDF ou image de la fiche d'aptitude",
    )

    document_name = fields.Char(
        string="Nom du fichier",
    )

    next_examination_date = fields.Date(
        string="Date prochain examen",
        compute="_compute_next_examination_date",
        readonly=True,
    )

    @api.depends('validity_days')
    def _compute_validity_breakdown(self):
        for wizard in self:
            days = wizard.validity_days or 0
            months = int(round(days / 30.0)) if days else 0
            extra_days = max(days - (months * 30), 0) if days else 0
            wizard.validity_months = months
            wizard.validity_extra_days = extra_days

    @api.depends('expiry_date')
    def _compute_next_examination_date(self):
        for wizard in self:
            wizard.next_examination_date = wizard.expiry_date

    @api.onchange('exam_type_id', 'examination_date')
    def _onchange_recalculate_expiry_date(self):
        """Automatically calculate expiry date when exam type or examination date changes"""
        if self.exam_type_id and self.exam_type_id.code == 'SPO':
            self.examination_date = fields.Date.today()

        if self.exam_type_id and self.examination_date and self.exam_type_id.validity_days:
            exam_date = self.examination_date
            if isinstance(exam_date, str):
                exam_date = fields.Date.from_string(exam_date)
            self.expiry_date = exam_date + timedelta(days=self.exam_type_id.validity_days)
        else:
            self.expiry_date = None

    @api.onchange('employee_id')
    def _onchange_load_latest_employee_fiche(self):
        if not self.employee_id:
            return

        latest_fiche = self.env['hr.fiche.aptitude'].search(
            [('employee_id', '=', self.employee_id.id), ('active', '=', True)],
            order='examination_date desc, id desc',
            limit=1,
        )
        
        if latest_fiche:
            # Pre-fill form fields from latest fiche if it exists
            self.doctor_name = latest_fiche.doctor_name
            self.medical_center = latest_fiche.medical_center
            self.restrictions = latest_fiche.restrictions
            self.notes = latest_fiche.notes
            self.aptitude_result = latest_fiche.aptitude_result
            self.aptitude_details = latest_fiche.aptitude_details
            self.examination_date = latest_fiche.examination_date
            if latest_fiche.exam_type_id:
                self.exam_type_id = latest_fiche.exam_type_id
        else:
            # Clear all fields if no existing fiche found for this employee
            self.doctor_name = False
            self.medical_center = False
            self.restrictions = False
            self.notes = False
            self.aptitude_result = False
            self.aptitude_details = False
            self.document = False
            self.document_name = False
            self.exam_type_id = False
            self.examination_date = fields.Date.today()
            
            # Return warning message
            return {
                'warning': {
                    'title': _('Aucune fiche d\'aptitude trouvée'),
                    'message': _("Cet employé n'a pas de fiche d'aptitude existante. Veuillez remplir tous les champs manuellement."),
                }
            }

    @api.depends('exam_type_id')
    def _compute_fiche_status(self):
        code_to_status = {
            'PER': 'periodique',
            'REP': 'reprise',
            'AVR': 'avant_reprise',
            'SPO': 'spontane',
            'EMB': 'embauche',
        }
        for record in self:
            record.fiche_status = code_to_status.get(record.exam_type_id.code)

    def action_create_medical_exam(self):
        """Create fiche d'amplitude record and close popup."""
        self.ensure_one()

        self.env['hr.fiche.aptitude'].create({
            'employee_id': self.employee_id.id,
            'exam_type_id': self.exam_type_id.id,
            'examination_date': self.examination_date,
            'expiry_date': self.expiry_date,
            'doctor_name': self.doctor_name,
            'medical_center': self.medical_center,
            'aptitude_result': self.aptitude_result,
            'aptitude_details': self.aptitude_details,
            'restrictions': self.restrictions,
            'notes': self.notes,
            'document': self.document,
            'document_name': self.document_name,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _("Fiche d'aptitude enregistrée."),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
