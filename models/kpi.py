# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date

class OHKPI(models.Model):
    _name = 'oh.kpi'
    _description = 'KPI Tracker'
    _rec_name = 'name'

    name = fields.Char(required=True)
    description = fields.Text()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    period = fields.Selection([('monthly','Monthly'),('quarterly','Quarterly'),('yearly','Yearly')], default='monthly')
    period_start = fields.Date()
    period_end = fields.Date()
    department_id = fields.Many2one('hr.department', string='Department')
    team = fields.Char()
    employee_id = fields.Many2one('hr.employee', string='Employee')
    target = fields.Float(required=True)
    actual = fields.Float(default=0.0)
    unit = fields.Char(default='')
    progress = fields.Float(compute='_compute_progress', store=True, digits=(6,2))
    status = fields.Selection([('ontrack','On Track'),('behind','Behind'),('done','Done')], compute='_compute_status', store=True)

    @api.depends('actual','target')
    def _compute_progress(self):
        for r in self:
            if not r.target:
                r.progress = 0.0
            else:
                r.progress = min(100.0, (r.actual / r.target) * 100.0)

    @api.depends('progress')
    def _compute_status(self):
        for r in self:
            if r.progress >= 100.0:
                r.status = 'done'
            elif r.progress >= 70.0:
                r.status = 'ontrack'
            else:
                r.status = 'behind'
