# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class OHAppraisalTemplate(models.Model):
    _name = 'oh.appraisal.template'
    _description = 'OH Appraisal Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence,id'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(tracking=True)
    template_type = fields.Selection([
        ('department', 'Department Template'),
        ('role', 'Role Template'),
        ('common', 'Common Template'),
        ('master', 'Master Template')
    ], string="Type", required=True, default='common', tracking=True)
    
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job Position')
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    common_factor = fields.Boolean('Common Factor', default=False)
    active = fields.Boolean(default=True)
    description = fields.Text("Description")

    line_ids = fields.One2many('oh.appraisal.template.line', 'template_id', 'Lines')
    
    @api.onchange('template_type')
    def _onchange_template_type(self):
        self.ensure_one()
        if self.template_type == 'department':
            self.job_id = False
            self.common_factor = False
        elif self.template_type == 'role':
            self.department_id = False
            self.common_factor = False
        elif self.template_type in ('common', 'master'):
            self.department_id = False
            self.job_id = False
            self.common_factor = True

class OHAppraisalTemplateLine(models.Model):
    _name = 'oh.appraisal.template.line' 
    _description = 'Appraisal Template Line'
    _order = 'sequence,id'

    sequence = fields.Integer('Sequence', default=10)
    template_id = fields.Many2one('oh.appraisal.template', 'Template', 
                                 required=True, ondelete='cascade')
    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    max_score = fields.Float('Max Score', default=5.0)
    weight = fields.Float('Weight', default=1.0)
    description = fields.Text("Description")