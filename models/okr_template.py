# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OHAppraisalOKRTemplate(models.Model):
    _name = 'oh.appraisal.okr.template'
    _description = 'OKR Template for Appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char('Template Name', required=False, tracking=True)
    code = fields.Char('Code', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company,
                                domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])
    
    description = fields.Html('Description')
    
    # Objective Section
    objective_title = fields.Char('Objective Title', required=False, tracking=True)
    objective_description = fields.Html('Objective Description', 
                                       help="Rich text description of the objective")
    priority = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], string='Priority', default='medium', required=True, tracking=True)
    
    objective_weightage = fields.Float('Objective Weightage (%)', 
                                      digits=(5, 2),
                                      default=100.0,
                                      help="Weightage of this objective in percentage")
    start_date = fields.Date('Start Date', required=False, tracking=True)
    end_date = fields.Date('End Date', required=False, tracking=True)

    department_id = fields.Many2one('hr.department', string='Department', 
                                  domain="[('company_id', '=', company_id)]",
                                  tracking=True,
                                  help="Department this OKR template applies to")
    
    team_id = fields.Many2one('oh.appraisal.team', string='Team',
                             domain="[('company_id', '=', company_id)]",
                             tracking=True,
                             help="Team this OKR template applies to")
    # Objective Weightages per Team
    weightage_ids = fields.One2many('oh.appraisal.okr.weightage',
                                'okr_template_id',
                                string='Objective Weightages')
    # Key Results
    key_result_ids = fields.One2many('oh.appraisal.okr.key.result', 
                                    'okr_template_id', 
                                    'Key Results')
    
    # Computed fields
    total_key_result_weightage = fields.Float('Total KR Weightage', 
                                             compute='_compute_total_weightage',
                                             store=True)
    key_result_count = fields.Integer('Key Results Count', 
                                     compute='_compute_key_result_count')

    @api.depends('key_result_ids.weightage')
    def _compute_total_weightage(self):
        for record in self:
            record.total_key_result_weightage = sum(
                record.key_result_ids.mapped('weightage')
            )

    @api.depends('key_result_ids')
    def _compute_key_result_count(self):
        for record in self:
            record.key_result_count = len(record.key_result_ids)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_("End Date cannot be before Start Date."))

    @api.constrains('objective_weightage')
    def _check_objective_weightage(self):
        for record in self:
            if record.objective_weightage < 0 or record.objective_weightage > 100:
                raise ValidationError(_("Objective Weightage must be between 0 and 100."))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            # Clear department and team if company changes
            if self.department_id and self.department_id.company_id != self.company_id:
                self.department_id = False
            if self.team_id and self.team_id.company_id != self.company_id:
                self.team_id = False
            
            # Update domains for department_id and team_id
            return {
                'domain': {
                    'department_id': [('company_id', '=', self.company_id.id)],
                    'team_id': [('company_id', '=', self.company_id.id)]
                }
            }
        else:
            self.department_id = False
            self.team_id = False
            return {
                'domain': {
                    'department_id': [],
                    'team_id': []
                }
            }


class OHAppraisalOKRKeyResult(models.Model):
    _name = 'oh.appraisal.okr.key.result'
    _description = 'OKR Key Result'
    _order = 'sequence, id'

    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     'OKR Template', 
                                     required=True, 
                                     ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    key_result_title = fields.Char('Key Result Title', required=True)
    metric = fields.Selection([
        ('percentage', '%'),
        ('count', 'Count'),
        ('rating', 'Rating'),
        ('score', 'Score')
    ], string='Metric/Measure', required=True, default='percentage')
    
    # Target Value fields
    target_operator = fields.Selection([
        ('eq', '='),
        ('ne', '≠'),
        ('gt', '>'),
        ('lt', '<'),
        ('gte', '≥'),
        ('lte', '≤')
    ], string='Target Operator', default='gte')
    target_value = fields.Float('Target Value', required=True)
    target_unit = fields.Char('Target Unit', help="e.g., rejections, sales, etc.")
    target_period = fields.Char('Target Period', help="e.g., in Q1, per month, etc.")
    
    # Actual Value fields
    actual_operator = fields.Selection([
        ('eq', '='),
        ('ne', '≠'),
        ('gt', '>'),
        ('lt', '<'),
        ('gte', '≥'),
        ('lte', '≤')
    ], string='Actual Operator', default='gte')
    actual_value = fields.Float('Actual Value')
    actual_unit = fields.Char('Actual Unit')
    actual_period = fields.Char('Actual Period')
    
    # Progress
    progress = fields.Float('Progress (%)', 
                           digits=(5, 2),
                           help="Auto-calculated progress percentage")
    
    weightage = fields.Float('Weightage (%)', 
                            digits=(5, 2),
                            default=25.0,
                            help="Weightage of this key result")
    
    data_source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('jira', 'Jira'),
        ('github', 'Github'),
        ('lms', 'LMS')
    ], string='Data Source', default='manual', required=True)

    # Display fields for better UX
    target_display = fields.Char('Target', compute='_compute_target_display', store=True)
    actual_display = fields.Char('Actual', compute='_compute_actual_display', store=True)

    @api.depends('target_operator', 'target_value', 'target_unit', 'target_period')
    def _compute_target_display(self):
        operator_map = {
            'eq': '=',
            'ne': '≠',
            'gt': '>',
            'lt': '<',
            'gte': '≥',
            'lte': '≤'
        }
        for record in self:
            parts = []
            if record.target_operator:
                parts.append(operator_map.get(record.target_operator, ''))
            parts.append(str(record.target_value))
            if record.target_unit:
                parts.append(record.target_unit)
            if record.target_period:
                parts.append(record.target_period)
            record.target_display = ' '.join(parts)

    @api.depends('actual_operator', 'actual_value', 'actual_unit', 'actual_period')
    def _compute_actual_display(self):
        operator_map = {
            'eq': '=',
            'ne': '≠',
            'gt': '>',
            'lt': '<',
            'gte': '≥',
            'lte': '≤'
        }
        for record in self:
            if not record.actual_value:
                record.actual_display = ''
                continue
            parts = []
            if record.actual_operator:
                parts.append(operator_map.get(record.actual_operator, ''))
            parts.append(str(record.actual_value))
            if record.actual_unit:
                parts.append(record.actual_unit)
            if record.actual_period:
                parts.append(record.actual_period)
            record.actual_display = ' '.join(parts)

    @api.constrains('weightage')
    def _check_weightage(self):
        for record in self:
            if record.weightage < 0 or record.weightage > 100:
                raise ValidationError(_("Weightage must be between 0 and 100."))