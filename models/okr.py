# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OKRObjective(models.Model):
    _name = 'oh.okr.objective'
    _description = 'Objective (OKR)'
    _rec_name = 'title'

    title = fields.Char(required=True)
    description = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    level = fields.Selection([('company','Company'),('department','Department'),('team','Team'),('individual','Individual')], default='individual')
    owner_id = fields.Many2one('res.users', string='Owner')
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_date = fields.Date()
    end_date = fields.Date()
    key_result_ids = fields.One2many('oh.okr.keyresult','objective_id', string='Key Results')
    progress = fields.Float(compute='_compute_progress', store=True, digits=(6,2))
    tag_ids = fields.Many2many('hr.skill', string='Tags/Skills')

    @api.depends('key_result_ids.progress')
    def _compute_progress(self):
        for rec in self:
            if not rec.key_result_ids:
                rec.progress = 0.0
            else:
                rec.progress = sum(rec.key_result_ids.mapped('progress'))/len(rec.key_result_ids)

class OKRKeyResult(models.Model):
    _name = 'oh.okr.keyresult'
    _description = 'Key Result'
    _rec_name = 'name'

    objective_id = fields.Many2one('oh.okr.objective', string='Objective', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    target_value = fields.Float(required=True)
    current_value = fields.Float(default=0.0)
    progress = fields.Float(compute='_compute_progress', store=True, digits=(6,2))
    unit = fields.Char(default='')
    owner_id = fields.Many2one('res.users', string='Owner')

    @api.depends('current_value','target_value')
    def _compute_progress(self):
        for rec in self:
            try:
                rec.progress = min(100.0, (rec.current_value / rec.target_value) * 100.0) if rec.target_value else 0.0
            except ZeroDivisionError:
                rec.progress = 0.0
