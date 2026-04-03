# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class HrFicheAptitude(models.Model):
    _name = 'hr.fiche.aptitude'
    _description = "Fiche d'aptitude au travail"
    _order = 'examination_date DESC'
    _rec_name = 'name'

    name = fields.Char(
        string="Référence",
        compute='_compute_name',
        store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string="Employé",
        required=True, ondelete='cascade', index=True,
    )
    exam_type_id = fields.Many2one(
        'medical.exam.type', string="Type d'examen",
        required=True, ondelete='restrict',
    )
    exam_type_code = fields.Char(
        related='exam_type_id.code', string="Code statut", readonly=True,
    )
    validity_days = fields.Integer(
        related='exam_type_id.validity_days', string="Durée (jours)", readonly=True,
    )
    validity_months = fields.Integer(
        string="Nb. mois", compute="_compute_validity_breakdown",
        readonly=True, store=True,
    )
    validity_extra_days = fields.Integer(
        string="Nb. jours", compute="_compute_validity_breakdown",
        readonly=True, store=True,
    )
    doctor_name = fields.Char(string="Nom du médecin")
    medical_center = fields.Char(string="Centre médical")
    examination_date = fields.Date(
        string="Date de l'examen", required=True, index=True,
    )
    expiry_date = fields.Date(string="Date d'expiration")
    next_examination_date = fields.Date(
        string="Date prochain examen",
        compute="_compute_next_examination_date", store=True,
    )
    fiche_status = fields.Selection([
        ('periodique', 'Périodique'),
        ('reprise', 'Reprise'),
        ('avant_reprise', 'Avant reprise'),
        ('spontane', 'Spontanée'),
        ('embauche', 'Embauche'),
    ], string="Statut", compute='_compute_fiche_status', store=True)

    aptitude_result = fields.Selection([
        ('apte_poste', 'Apte au poste'),
        ('apte_amenagement', "Apte avec aménagement du poste"),
        ('inapte_temp', 'Inapte temporairement au poste'),
        ('apte_changement', "Apte après changement du poste"),
        ('inapte_def', "Inapte définitif à tout poste"),
    ], string="Conclusion d'aptitude")

    aptitude_details = fields.Text(string="Précisions / recommandations")
    restrictions = fields.Text(string="Restrictions de travail")
    notes = fields.Text(string="Notes du médecin")
    document = fields.Binary(string="Document de la fiche", attachment=True)
    document_name = fields.Char(string="Nom du fichier")
    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
        help="La fiche la plus récente de l'employé reste active, les anciennes sont archivées.",
    )
    create_date = fields.Datetime(string="Date de création", readonly=True)

    @api.depends('employee_id', 'examination_date')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.examination_date:
                rec.name = "FICHE-%s-%s" % (rec.employee_id.name, rec.examination_date)
            else:
                rec.name = "FICHE-NOUVELLE"

    @api.depends('validity_days')
    def _compute_validity_breakdown(self):
        for rec in self:
            d = rec.validity_days or 0
            m = int(round(d / 30.0)) if d else 0
            rec.validity_months = m
            rec.validity_extra_days = max(d - (m * 30), 0) if d else 0

    @api.depends('expiry_date')
    def _compute_next_examination_date(self):
        for rec in self:
            rec.next_examination_date = rec.expiry_date

    @api.depends('exam_type_id')
    def _compute_fiche_status(self):
        mapping = {
            'PER': 'periodique', 'REP': 'reprise',
            'AVR': 'avant_reprise', 'SPO': 'spontane', 'EMB': 'embauche',
        }
        for rec in self:
            rec.fiche_status = mapping.get(
                rec.exam_type_id.code, False
            ) if rec.exam_type_id else False

    def _compute_expiry_from_exam(self, exam_type_rec, exam_date_val):
        """Safely compute expiry date using timedelta."""
        if not exam_type_rec or not exam_date_val:
            return False
        nb = exam_type_rec.validity_days
        if not nb or nb <= 0:
            return False
        if isinstance(exam_date_val, str):
            exam_date_val = fields.Date.to_date(exam_date_val)
        return exam_date_val + timedelta(days=int(nb))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('expiry_date'):
                if vals.get('exam_type_id') and vals.get('examination_date'):
                    et = self.env['medical.exam.type'].browse(vals['exam_type_id'])
                    computed = self._compute_expiry_from_exam(et, vals['examination_date'])
                    if computed:
                        vals['expiry_date'] = computed
            # Archive les anciennes fiches de l'employé
            employee_id = vals.get('employee_id')
            if employee_id:
                old_fiches = self.search([
                    ('employee_id', '=', employee_id),
                    ('active', '=', True),
                ])
                if old_fiches:
                    old_fiches.write({'active': False})
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'expiry_date' not in vals:
            if 'exam_type_id' in vals or 'examination_date' in vals:
                for rec in self:
                    computed = rec._compute_expiry_from_exam(
                        rec.exam_type_id, rec.examination_date
                    )
                    if computed:
                        rec.expiry_date = computed
        return res
    @api.model
    def _cleanup_and_archive_old_fiches(self):
        """Archive les fiches anciennes pour chaque employé, garder seulement la plus récente."""
        # Récupérer tous les employés ayant des fiches
        employees = self.env['hr.employee'].search([])
        
        for employee in employees:
            # Récupérer toutes les fiches de l'employé, triées par date d'examen (recent d'abord)
            fiches = self.search(
                [('employee_id', '=', employee.id)],
                order='examination_date desc',
            )
            
            # Si plus d'une fiche, archiver les anciennes
            if len(fiches) > 1:
                old_fiches = fiches[1:]  # Garder la première (la plus récente)
                old_fiches.write({'active': False})