# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OHAppraisalIndustry(models.Model):
    _name = 'oh.appraisal.industry'
    _description = 'Industry Types for Appraisal'
    _order = 'sequence,id'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description')
    active = fields.Boolean(default=True)
