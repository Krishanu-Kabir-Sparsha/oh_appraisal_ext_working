# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class OHAppraisalDepartmentWeightage(models.Model):
    _name = 'oh.appraisal.department.weightage'
    _description = 'Department Weightage Configuration'
    _rec_name = 'department_id'

    company_id = fields.Many2one('res.company', required=True, 
                                default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', required=True,
                                   domain="[('company_id', '=', company_id)]")
    
    # Weightage fields without defaults
    functional_weightage = fields.Float('Department Weightage (%)', 
                                      digits=(5, 2),
                                      default=0.0,
                                      required=True)
    role_weightage = fields.Float('Role Weightage (%)', 
                                digits=(5, 2),
                                default=0.0,
                                required=True)
    common_weightage = fields.Float('Common Weightage (%)', 
                                  digits=(5, 2),
                                  default=0.0,
                                  required=True)
    
    # Additional configuration fields
    assessment_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], string='Assessment Period', default='annual')
    
    industry_type = fields.Many2one('oh.appraisal.industry', string='Industry Type')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_department_company', 
         'unique(department_id, company_id)', 
         'Only one configuration allowed per department per company.')
    ]

    @api.constrains('functional_weightage', 'role_weightage', 'common_weightage')
    def _check_weightages(self):
        for record in self:
            total = sum([
                record.functional_weightage or 0.0,
                record.role_weightage or 0.0,
                record.common_weightage or 0.0
            ])
            if abs(total - 100.0) > 0.01:
                raise ValidationError(
                    _("Total weightage must equal 100%%. Current total: %.2f%%") % total
                )

    @api.model
    def save_department_config(self, department_id, company_id, values):
        """Save complete department configuration from dashboard"""
        if not department_id or not company_id:
            return False
                
        existing = self.search([
            ('department_id', '=', department_id),
            ('company_id', '=', company_id)
        ], limit=1)
        
        config_values = {
            'department_id': department_id,
            'company_id': company_id,
            'functional_weightage': values.get('functional_weightage', 0.0),
            'role_weightage': values.get('role_weightage', 0.0),
            'common_weightage': values.get('common_weightage', 0.0),
            'assessment_period': values.get('assessment_period', 'annual'),
            'industry_type': values.get('industry_type', False),
        }
        
        try:
            if existing:
                existing.write(config_values)
                return existing.id
            else:
                new_config = self.create(config_values)
                return new_config.id
        except Exception as e:
            _logger.error("Error saving department configuration: %s", str(e))
            return False

    @api.model
    def get_department_config(self, department_id, company_id):
        """Get weightage configuration for a department"""
        config = self.search([
            ('department_id', '=', department_id),
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
        
        if config:
            return {
                'functional_weightage': float(config.functional_weightage or 0.0),
                'role_weightage': float(config.role_weightage or 0.0),
                'common_weightage': float(config.common_weightage or 0.0),
                'assessment_period': config.assessment_period or 'annual',
            }
        return False
        