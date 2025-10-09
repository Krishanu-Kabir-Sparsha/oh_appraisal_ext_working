# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OHAppraisalOKRWeightage(models.Model):
    _name = 'oh.appraisal.okr.weightage'
    _description = 'OKR Objective Weightage per Team'
    _order = 'sequence, id'

    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     'OKR Template', 
                                     required=True, 
                                     ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    team_id = fields.Many2one('oh.appraisal.team', 
                             string='Team',
                             required=True,
                             domain="[('company_id', '=', company_id)]")
    
    company_id = fields.Many2one('res.company', 
                                related='okr_template_id.company_id',
                                store=True,
                                string='Company')
    
    department_weightage = fields.Float('Department Weightage (%)', 
                                       digits=(5, 2),
                                       default=35.0,
                                       help="Weightage for department/functional items")
    
    role_weightage = fields.Float('Role Weightage (%)', 
                                  digits=(5, 2),
                                  default=45.0,
                                  help="Weightage for role-based items")
    
    common_weightage = fields.Float('Common Weightage (%)', 
                                   digits=(5, 2),
                                   default=20.0,
                                   help="Weightage for common/org-wide items")
    
    total_weightage = fields.Float('Total (%)', 
                                  compute='_compute_total_weightage',
                                  store=True)

    @api.depends('department_weightage', 'role_weightage', 'common_weightage')
    def _compute_total_weightage(self):
        for record in self:
            record.total_weightage = (record.department_weightage + 
                                     record.role_weightage + 
                                     record.common_weightage)

    @api.constrains('department_weightage', 'role_weightage', 'common_weightage')
    def _check_weightages(self):
        for record in self:
            total = (record.department_weightage + 
                    record.role_weightage + 
                    record.common_weightage)
            if abs(total - 100.0) > 0.01:
                raise ValidationError(
                    _("Total weightage must equal 100%%. Current total: %.2f%%") % total
                )
            
            if (record.department_weightage < 0 or 
                record.role_weightage < 0 or 
                record.common_weightage < 0):
                raise ValidationError(_("Weightages cannot be negative."))

    _sql_constraints = [
        ('team_okr_uniq', 'unique(okr_template_id, team_id)', 
         'Each team can only have one weightage configuration per OKR template.')
    ]