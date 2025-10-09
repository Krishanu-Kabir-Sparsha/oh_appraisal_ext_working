# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OHAppraisalTeam(models.Model):
    _name = 'oh.appraisal.team'
    _description = 'Appraisal Team'
    _order = 'sequence, id'

    name = fields.Char('Team Name', required=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company',
                                default=lambda self: self.env.company,
                                domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])
    department_id = fields.Many2one('hr.department', 'Department',
                                   domain="[('company_id', '=', company_id)]")
    member_ids = fields.Many2many('hr.employee', 
                              'oh_appraisal_team_employee_rel', 
                              'team_id', 
                              'employee_id',
                              string='Team Members',
                              domain="[('company_id', '=', company_id), ('department_id', '=', department_id)]")
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'A team with this name already exists for this company.')
    ]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            if self.department_id and self.department_id.company_id != self.company_id:
                self.department_id = False
            self.member_ids = False
            
            domain_members = [('company_id', '=', self.company_id.id)]
            if self.department_id:
                domain_members.append(('department_id', '=', self.department_id.id))
                
            return {
                'domain': {
                    'department_id': [('company_id', '=', self.company_id.id)],
                    'member_ids': domain_members
                }
            }
        else:
            self.department_id = False
            self.member_ids = False
            return {
                'domain': {
                    'department_id': [],
                    'member_ids': []
                }
            }

    @api.onchange('department_id')
    def _onchange_department_id(self):
        # Clear members when department changes
        self.member_ids = False
        if self.department_id and self.company_id:
            return {
                'domain': {
                    'member_ids': [('company_id', '=', self.company_id.id), ('department_id', '=', self.department_id.id)]
                }
            }
        elif self.company_id:
            return {
                'domain': {
                    'member_ids': [('company_id', '=', self.company_id.id)]
                }
            }
        else:
            return {
                'domain': {
                    'member_ids': []
                }
            }