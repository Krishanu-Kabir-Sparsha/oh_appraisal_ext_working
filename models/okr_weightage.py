# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OHAppraisalOKRWeightage(models.Model):
    _name = 'oh.appraisal.okr.weightage'
    _description = 'OKR Objective Weightage per Team'
    _order = 'sequence, id'

    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     required=True, 
                                     ondelete='cascade')
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related='okr_template_id.company_id', 
                                string='Company',
                                store=True,
                                readonly=True)
    team_id = fields.Many2one('oh.appraisal.team', 
                             string='Team',
                             required=True,
                             domain="[('company_id', '=', company_id), "
                                    "('department_id', '=', parent.department_id)]")
    
    department_weightage = fields.Float('Department Weightage (%)', 
                                      digits=(5, 2))
    role_weightage = fields.Float('Role Weightage (%)', 
                                 digits=(5, 2))
    common_weightage = fields.Float('Common Weightage (%)', 
                                  digits=(5, 2))
    
    available_dept_weightage = fields.Float(compute='_compute_available_weightages')
    available_role_weightage = fields.Float(compute='_compute_available_weightages')
    available_common_weightage = fields.Float(compute='_compute_available_weightages')

    @api.depends('okr_template_id.department_id', 'okr_template_id.company_id')
    def _compute_available_weightages(self):
        for record in self:
            dept_config = self.env['oh.appraisal.department.weightage'].search([
                ('department_id', '=', record.okr_template_id.department_id.id),
                ('company_id', '=', record.okr_template_id.company_id.id)
            ], limit=1)
            
            if dept_config:
                record.available_dept_weightage = dept_config.functional_weightage
                record.available_role_weightage = dept_config.role_weightage
                record.available_common_weightage = dept_config.common_weightage
            else:
                record.available_dept_weightage = 0.0
                record.available_role_weightage = 0.0
                record.available_common_weightage = 0.0

    @api.constrains('department_weightage', 'role_weightage', 'common_weightage')
    def _check_weightages(self):
        for record in self:
            if not record.okr_template_id.department_id:
                continue
                
            dept_config = self.env['oh.appraisal.department.weightage'].search([
                ('department_id', '=', record.okr_template_id.department_id.id),
                ('company_id', '=', record.okr_template_id.company_id.id)
            ], limit=1)
            
            if not dept_config:
                raise ValidationError(_("No weightage configuration found for the department."))
            
            # Calculate total allocated weightages for this OKR template
            domain = [
                ('okr_template_id', '=', record.okr_template_id.id),
                ('id', '!=', record.id)  # Exclude current record
            ]
            other_weightages = self.search(domain)
            
            total_dept = sum(other_weightages.mapped('department_weightage')) + record.department_weightage
            total_role = sum(other_weightages.mapped('role_weightage')) + record.role_weightage
            total_common = sum(other_weightages.mapped('common_weightage')) + record.common_weightage
            
            if total_dept > dept_config.functional_weightage:
                raise ValidationError(_("Total department weightage exceeds available budget (%.2f%%)") 
                                   % dept_config.functional_weightage)
            
            if total_role > dept_config.role_weightage:
                raise ValidationError(_("Total role weightage exceeds available budget (%.2f%%)")
                                   % dept_config.role_weightage)
            
            if total_common > dept_config.common_weightage:
                raise ValidationError(_("Total common weightage exceeds available budget (%.2f%%)")
                                   % dept_config.common_weightage)

            
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Redistribute common weightage after creation
        if records:
            records[0].okr_template_id._redistribute_common_weightage()
        return records

    def unlink(self):
        templates = self.mapped('okr_template_id')
        res = super().unlink()
        # Redistribute common weightage after deletion
        for template in templates:
            template._redistribute_common_weightage()
        return res

    @api.onchange('team_id')
    def _onchange_team_id(self):
        if self.team_id:
            self.okr_template_id._redistribute_common_weightage()


    @api.constrains('team_id')
    def _check_team_department(self):
        for record in self:
            if record.team_id.department_id != record.okr_template_id.department_id:
                raise ValidationError(_("Selected team must belong to the template's department."))

    @api.onchange('team_id')
    def _onchange_team_id(self):
        if not self.team_id:
            self.department_weightage = 0.0
            self.role_weightage = 0.0
            self.common_weightage = 0.0