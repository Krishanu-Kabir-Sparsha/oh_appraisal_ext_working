# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OHAppraisalPrimaryFramework(models.Model):
    _name = 'oh.appraisal.primary.framework'
    _description = 'Primary Framework Template'
    _order = 'sequence,id'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    description = fields.Text('Description')
    framework_type = fields.Selection([
        ('360_degree', '360-Degree Feedback'),
        ('kpi_based', 'KPI-Based'),
        ('competency', 'Competency-Based'),
        ('mbo', 'Management by Objectives'),
        ('balanced_scorecard', 'Balanced Scorecard')
    ], string='Framework Type', required=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)