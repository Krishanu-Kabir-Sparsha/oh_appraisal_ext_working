# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class OHAppraisalOKRTemplate(models.Model):
    _name = 'oh.appraisal.okr.template'
    _description = 'OKR Template for Appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char('Template Name', required=False, tracking=True)
    goal = fields.Char('Goal', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company,
                                domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])
    
    description = fields.Html('Description')
    
    # Objective Section
    objective_title = fields.Char('Objective Title', required=False, tracking=True)
    objective_breakdown_ids = fields.One2many(
        'oh.appraisal.objective.breakdown',
        'okr_template_id',
        string='Objective Breakdowns'
    )
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

    # Add index for department_id
    department_id = fields.Many2one(
        'hr.department', 
        string='Department',
        index=True,  # Add this line
        domain="[('company_id', '=', company_id)]",
        tracking=True,
        help="Department this OKR template applies to"
    )
    
    team_id = fields.Many2one('oh.appraisal.team', string='Team',
                             domain="[('company_id', '=', company_id), "
                                   "('department_id', '=', department_id)]",
                             tracking=True,
                             help="Team this OKR template applies to")
    
    available_team_ids = fields.Many2many('oh.appraisal.team', compute='_compute_available_teams')

    # Objective Weightages per Team
    weightage_ids = fields.One2many('oh.appraisal.okr.weightage',
                                   'okr_template_id',
                                   string='Objective Weightages')
    
    # Department Budget Information
    department_budget_functional = fields.Float('Dept Budget (%)',
                                             compute='_compute_department_budget',
                                             help="Total budget for department weightage")
    department_budget_role = fields.Float('Role Budget (%)',
                                        compute='_compute_department_budget',
                                        help="Total budget for role weightage")
    department_budget_common = fields.Float('Common Budget (%)',
                                          compute='_compute_department_budget',
                                          help="Total budget for common weightage")

    allocated_functional = fields.Float('Allocated Dept (%)',
                                      compute='_compute_allocated_weightages')
    allocated_role = fields.Float('Allocated Role (%)',
                                compute='_compute_allocated_weightages')
    allocated_common = fields.Float('Allocated Common (%)',
                                  compute='_compute_allocated_weightages')

    
    # Update One2many fields with proper domains
    department_key_result_ids = fields.One2many(
        'oh.appraisal.okr.key.result',
        'okr_template_id',
        domain=[('result_type', '=', 'department')],
        context={'weightage_type': 'department', 'default_result_type': 'department'}
    )
    
    role_key_result_ids = fields.One2many(
        'oh.appraisal.okr.key.result',
        'okr_template_id',
        domain=[('result_type', '=', 'role')],
        context={'weightage_type': 'role', 'default_result_type': 'role'}
    )
    
    common_key_result_ids = fields.One2many(
        'oh.appraisal.okr.key.result',
        'okr_template_id',
        domain=[('result_type', '=', 'common')],
        context={'weightage_type': 'common', 'default_result_type': 'common'}
    )

    # Key Results
    # Update the original field to show all records
    key_result_ids = fields.One2many(
        'oh.appraisal.okr.key.result',
        'okr_template_id',
        string='All Key Results'
    )
    # # Computed fields
    # total_key_result_weightage = fields.Float('Total KR Weightage', 
    #                                         compute='_compute_total_weightage',
    #                                         store=True)
    key_result_count = fields.Integer('Key Results Count', 
                                    compute='_compute_key_result_count')

    @api.depends('department_id', 'company_id')
    def _compute_department_budget(self):
        for record in self:
            if record.department_id and record.company_id:
                config = self.env['oh.appraisal.department.weightage'].search([
                    ('department_id', '=', record.department_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('active', '=', True)
                ], limit=1)
                
                if config:
                    record.department_budget_functional = config.functional_weightage
                    record.department_budget_role = config.role_weightage
                    record.department_budget_common = config.common_weightage
                else:
                    record.department_budget_functional = 0.0
                    record.department_budget_role = 0.0
                    record.department_budget_common = 0.0
            else:
                record.department_budget_functional = 0.0
                record.department_budget_role = 0.0
                record.department_budget_common = 0.0

    @api.depends('weightage_ids.department_weightage', 
                'weightage_ids.role_weightage',
                'weightage_ids.common_weightage')
    def _compute_allocated_weightages(self):
        for record in self:
            record.allocated_functional = sum(record.weightage_ids.mapped('department_weightage'))
            record.allocated_role = sum(record.weightage_ids.mapped('role_weightage'))
            record.allocated_common = sum(record.weightage_ids.mapped('common_weightage'))

    # @api.depends('key_result_ids.weightage')
    # def _compute_total_weightage(self):
    #     for record in self:
    #         record.total_key_result_weightage = sum(
    #             record.key_result_ids.mapped('weightage')
    #         )

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

    @api.constrains('weightage_ids')
    def _check_weightage_totals(self):
        for record in self:
            if not record.department_id:
                continue

            total_dept = sum(record.weightage_ids.mapped('department_weightage'))
            total_role = sum(record.weightage_ids.mapped('role_weightage'))
            total_common = sum(record.weightage_ids.mapped('common_weightage'))

            if total_dept > record.department_budget_functional:
                raise ValidationError(_("Total department weightage (%s%%) exceeds available budget (%s%%)") % 
                                    (total_dept, record.department_budget_functional))
            if total_role > record.department_budget_role:
                raise ValidationError(_("Total role weightage (%s%%) exceeds available budget (%s%%)") % 
                                    (total_role, record.department_budget_role))
            if total_common > record.department_budget_common:
                raise ValidationError(_("Total common weightage (%s%%) exceeds available budget (%s%%)") % 
                                    (total_common, record.department_budget_common))

   
    @api.constrains('weightage_ids')
    def _check_weightage_distribution(self):
        for record in self:
            if record.weightage_ids:
                total_dept = sum(record.weightage_ids.mapped('department_weightage'))
                total_role = sum(record.weightage_ids.mapped('role_weightage'))
                total_common = sum(record.weightage_ids.mapped('common_weightage'))

                if total_dept > record.department_budget_functional:
                    raise ValidationError(_("Total department weightage cannot exceed budget"))
                if total_role > record.department_budget_role:
                    raise ValidationError(_("Total role weightage cannot exceed budget"))
                if abs(total_common - record.department_budget_common) > 0.01:
                    # Redistribute common weightage if it doesn't match budget
                    record._redistribute_common_weightage()
   
    
    @api.constrains('department_weightage', 'role_weightage', 'common_weightage')
    def _check_weightage_limits(self):
        for record in self:
            if not record.okr_template_id.department_id:
                continue

            # Get all weightages for this template
            template_weightages = record.okr_template_id.weightage_ids

            # Calculate totals including current record
            total_dept = sum(template_weightages.mapped('department_weightage'))
            total_role = sum(template_weightages.mapped('role_weightage'))
            total_common = sum(template_weightages.mapped('common_weightage'))

            # Get available budgets
            available_dept = record.okr_template_id.department_budget_functional
            available_role = record.okr_template_id.department_budget_role
            available_common = record.okr_template_id.department_budget_common

            # Check department weightage
            if total_dept > available_dept:
                raise ValidationError(_(
                    "Total Department Weightage (%.2f%%) exceeds available budget (%.2f%%).\n"
                    "Please reduce the allocation to stay within budget."
                ) % (total_dept, available_dept))

            # Check role weightage
            if total_role > available_role:
                raise ValidationError(_(
                    "Total Role Weightage (%.2f%%) exceeds available budget (%.2f%%).\n"
                    "Please reduce the allocation to stay within budget."
                ) % (total_role, available_role))

            # Check common weightage
            if total_common > available_common:
                raise ValidationError(_(
                    "Total Common Weightage (%.2f%%) exceeds available budget (%.2f%%).\n"
                    "Please reduce the allocation to stay within budget."
                ) % (total_common, available_common))

    @api.onchange('department_weightage', 'role_weightage', 'common_weightage')
    def _onchange_weightages(self):
        """Show warning if weightages exceed budget"""
        warning = {}
        if self.okr_template_id.department_id:
            # Calculate totals
            template_weightages = self.okr_template_id.weightage_ids
            total_dept = sum(template_weightages.mapped('department_weightage'))
            total_role = sum(template_weightages.mapped('role_weightage'))
            total_common = sum(template_weightages.mapped('common_weightage'))

            # Get available budgets
            available_dept = self.okr_template_id.department_budget_functional
            available_role = self.okr_template_id.department_budget_role
            available_common = self.okr_template_id.department_budget_common

            warning_messages = []

            # Check each type of weightage
            if total_dept > available_dept:
                warning_messages.append(
                    f"Department Weightage: {total_dept:.2f}% exceeds budget of {available_dept:.2f}%"
                )
            if total_role > available_role:
                warning_messages.append(
                    f"Role Weightage: {total_role:.2f}% exceeds budget of {available_role:.2f}%"
                )
            if total_common > available_common:
                warning_messages.append(
                    f"Common Weightage: {total_common:.2f}% exceeds budget of {available_common:.2f}%"
                )

            if warning_messages:
                warning = {
                    'title': _('Weightage Allocation Warning'),
                    'message': _("The following allocations exceed their budgets:\n\n• ") + 
                              "\n• ".join(warning_messages)
                }
                return {'warning': warning}

    
    @api.onchange('company_id', 'department_id')
    def _onchange_company_department(self):
        """Handle changes in company or department selection"""
        if self.weightage_ids:
            # Store current weightages before changing
            self._store_current_weightages()
        
        if self.company_id:
            if self.department_id and self.department_id.company_id != self.company_id:
                self.department_id = False
            if self.team_id and self.team_id.company_id != self.company_id:
                self.team_id = False
            
            domain = [('company_id', '=', self.company_id.id)]
            if self.department_id:
                domain.append(('department_id', '=', self.department_id.id))
                # Load stored weightages for this department if they exist
                self._load_department_weightages()
            else:
                self.weightage_ids = [(5, 0, 0)]
            
            return {
                'domain': {
                    'department_id': [('company_id', '=', self.company_id.id)],
                    'team_id': domain
                }
            }
        else:
            self.department_id = False
            self.team_id = False
            self.weightage_ids = [(5, 0, 0)]
            return {
                'domain': {
                    'department_id': [],
                    'team_id': []
                }
            }

    def _store_current_weightages(self):
        """Store current weightage configuration for the department"""
        if not self.department_id:
            return
        
        # Store as JSON in ir.config_parameter
        key = f'okr_weightages_dept_{self.department_id.id}'
        weightages_data = [{
            'team_id': w.team_id.id,
            'department_weightage': w.department_weightage,
            'role_weightage': w.role_weightage,
            'common_weightage': w.common_weightage
        } for w in self.weightage_ids]
        
        self.env['ir.config_parameter'].sudo().set_param(
            key, json.dumps(weightages_data)
        )

    def _load_department_weightages(self):
        """Load stored weightage configuration for the department"""
        if not self.department_id:
            return
        
        key = f'okr_weightages_dept_{self.department_id.id}'
        stored_data = self.env['ir.config_parameter'].sudo().get_param(key)
        
        if stored_data:
            try:
                weightages_data = json.loads(stored_data)
                weightage_vals = []
                
                # Get current teams for validation
                available_teams = self.env['oh.appraisal.team'].search([
                    ('company_id', '=', self.company_id.id),
                    ('department_id', '=', self.department_id.id)
                ])
                available_team_ids = available_teams.ids
                
                # Create weightage records for stored data
                for data in weightages_data:
                    if data['team_id'] in available_team_ids:
                        weightage_vals.append((0, 0, {
                            'team_id': data['team_id'],
                            'department_weightage': data['department_weightage'],
                            'role_weightage': data['role_weightage'],
                            'common_weightage': data['common_weightage']
                        }))
                
                # Add new teams with default values
                existing_team_ids = [w['team_id'] for w in weightages_data]
                new_teams = available_teams.filtered(lambda t: t.id not in existing_team_ids)
                
                if new_teams:
                    team_count = len(new_teams)
                    common_per_team = self.department_budget_common / team_count if team_count > 0 else 0
                    
                    for team in new_teams:
                        weightage_vals.append((0, 0, {
                            'team_id': team.id,
                            'department_weightage': 0.0,
                            'role_weightage': 0.0,
                            'common_weightage': round(common_per_team, 2)
                        }))
                
                self.weightage_ids = weightage_vals
                
            except Exception as e:
                _logger.error("Error loading department weightages: %s", str(e))
                self._create_default_weightages()
        else:
            self._create_default_weightages()

    def _create_default_weightages(self):
        """Create default weightage records for available teams"""
        if not self.department_id:
            return
            
        teams = self.env['oh.appraisal.team'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ])
        
        if teams:
            weightage_vals = []
            team_count = len(teams)
            common_per_team = self.department_budget_common / team_count if team_count > 0 else 0
            
            for team in teams:
                weightage_vals.append((0, 0, {
                    'team_id': team.id,
                    'department_weightage': 0.0,
                    'role_weightage': 0.0,
                    'common_weightage': round(common_per_team, 2)
                }))
            
            self.weightage_ids = weightage_vals
            # Ensure proper distribution after creation
            self._redistribute_common_weightage()
    

    def _redistribute_common_weightage(self):
        """
        Redistribute common weightage equally among teams.
        The total common weightage from department budget will be divided equally among all teams.
        """
        for record in self:
            if not record.weightage_ids or not record.department_id:
                continue

            # Get total common weightage from department budget
            total_common = record.department_budget_common
            team_count = len(record.weightage_ids)
            
            if team_count > 0:
                # Calculate equal share for each team
                weight_per_team = total_common / team_count
                # Round to 2 decimal places
                weight_per_team = round(weight_per_team, 2)
                
                # Update all weightage records
                for weightage in record.weightage_ids:
                    weightage.write({'common_weightage': weight_per_team})
                
                # Handle any rounding discrepancy
                total_allocated = sum(record.weightage_ids.mapped('common_weightage'))
                if abs(total_allocated - total_common) > 0.01:
                    # Distribute the remaining amount to the first record
                    difference = total_common - total_allocated
                    if record.weightage_ids:
                        record.weightage_ids[0].write({
                            'common_weightage': record.weightage_ids[0].common_weightage + round(difference, 2)
                        })

    @api.model
    def _ensure_common_weightage_distribution(self):
        """Ensure common weightage is properly distributed after changes"""
        for record in self:
            if record.weightage_ids:
                total_common = sum(record.weightage_ids.mapped('common_weightage'))
                if abs(total_common - record.department_budget_common) > 0.01:
                    record._redistribute_common_weightage()


    def _check_weightage_allocation(self):
        """Validate total weightage allocation"""
        self.ensure_one()
        if not self.department_id:
            return True

        total_dept = sum(self.weightage_ids.mapped('department_weightage'))
        total_role = sum(self.weightage_ids.mapped('role_weightage'))
        total_common = sum(self.weightage_ids.mapped('common_weightage'))

        if total_dept > self.department_budget_functional:
            raise ValidationError(_(
                "Total Department Weightage (%.2f%%) cannot exceed available budget (%.2f%%)."
            ) % (total_dept, self.department_budget_functional))

        if total_role > self.department_budget_role:
            raise ValidationError(_(
                "Total Role Weightage (%.2f%%) cannot exceed available budget (%.2f%%)."
            ) % (total_role, self.department_budget_role))

        if total_common > self.department_budget_common:
            raise ValidationError(_(
                "Total Common Weightage (%.2f%%) cannot exceed available budget (%.2f%%)."
            ) % (total_common, self.department_budget_common))

        return True
    
    @api.constrains('weightage_ids')
    def _check_weightage_ids(self):
        for record in self:
            record._check_weightage_allocation()


    @api.onchange('department_id')
    def _onchange_department(self):
        """Handle department change"""
        if self.department_id:
            # Clear existing weightage records when department changes
            self.weightage_ids = [(5, 0, 0)]  # Clear all records
            
            # Update team domain
            return {
                'domain': {
                    'team_id': [
                        ('company_id', '=', self.company_id.id),
                        ('department_id', '=', self.department_id.id)
                    ]
                }
            }
        else:
            self.weightage_ids = [(5, 0, 0)]
            self.team_id = False
            return {
                'domain': {
                    'team_id': [('company_id', '=', self.company_id.id)]
                }
            }


    @api.depends('company_id', 'department_id')
    def _compute_available_teams(self):
        """Compute available teams based on selected department"""
        for record in self:
            domain = [('company_id', '=', record.company_id.id)]
            if record.department_id:
                domain.append(('department_id', '=', record.department_id.id))
            record.available_team_ids = self.env['oh.appraisal.team'].search(domain)

    
    @api.onchange('weightage_ids')
    def _onchange_weightage_ids(self):
        """When weightages change, redistribute common weightage and recompute"""
        for record in self:
            # First redistribute common weightage
            record._redistribute_common_weightage()
            # Then trigger recompute of available weightages
            if record.department_key_result_ids:
                for kr in record.department_key_result_ids:
                    kr._compute_available_weightage()
            if record.role_key_result_ids:
                for kr in record.role_key_result_ids:
                    kr._compute_available_weightage()
            if record.common_key_result_ids:
                for kr in record.common_key_result_ids:
                    kr._compute_available_weightage()

    # def write(self, vals):
    #     """Override write to handle weightage updates"""
    #     res = super().write(vals)
    #     if 'weightage_ids' in vals:
    #         self.mapped('key_result_ids')._compute_weightage()
    #     return res
    

    @api.depends('objective_breakdown_ids')
    def _compute_breakdown_count(self):
        for record in self:
            record.breakdown_count = len(record.objective_breakdown_ids)

    breakdown_count = fields.Integer(
        string='Breakdown Items',
        compute='_compute_breakdown_count',
        store=True
    )

    def action_view_breakdowns(self):
        self.ensure_one()
        return {
            'name': _('Objective Breakdowns'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'oh.appraisal.objective.breakdown',
            'domain': [('okr_template_id', '=', self.id)],
            'context': {'default_okr_template_id': self.id},
        }

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._redistribute_common_weightage()
        return record

    def write(self, vals):
        """Override write to handle weightage updates and redistribution"""
        res = super().write(vals)
        if 'weightage_ids' in vals:
            self._redistribute_common_weightage()
            # Update available weightages for all key results
            for record in self:
                if record.department_key_result_ids:
                    for kr in record.department_key_result_ids:
                        kr._compute_available_weightage()
                if record.role_key_result_ids:
                    for kr in record.role_key_result_ids:
                        kr._compute_available_weightage()
                if record.common_key_result_ids:
                    for kr in record.common_key_result_ids:
                        kr._compute_available_weightage()
        return res


class OHAppraisalDepartmentWeightageStore(models.Model):
    _name = 'oh.appraisal.department.weightage.store'
    _description = 'Department Weightage Storage'

    okr_template_id = fields.Many2one('oh.appraisal.okr.template', required=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', required=True)
    company_id = fields.Many2one('res.company', related='okr_template_id.company_id', store=True)
    stored_data = fields.Text('Stored Weightages')
    
    _sql_constraints = [
        ('unique_template_dept', 'unique(okr_template_id, department_id)',
         'Only one weightage configuration per department per template!')
    ]



class OHAppraisalOKRKeyResult(models.Model):
    _name = 'oh.appraisal.okr.key.result'
    _description = 'OKR Key Result'
    _order = 'sequence, id'

    result_type = fields.Selection([
        ('department', 'Department'),
        ('role', 'Role'),
        ('common', 'Common')
    ], string='Result Type', required=True, default='department')

    # Add the team field after okr_template_id
    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     'OKR Template', 
                                     required=True, 
                                     ondelete='cascade')
    team_id = fields.Many2one('oh.appraisal.team', 
                             string='Team',
                             domain="[('company_id', '=', parent.company_id), "
                                   "('department_id', '=', parent.department_id)]")
    sequence = fields.Integer('Sequence', default=10)
    
    key_objective_breakdown = fields.Many2one(
        'oh.appraisal.objective.breakdown',
        string='Objective Breakdown',
        required=True,
        domain="[('okr_template_id', '=', okr_template_id)]"
    )

    breakdown_priority = fields.Selection(
        related='key_objective_breakdown.priority',
        string='Priority',
        store=True,
        readonly=True
    )
    
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
    
    # Updated progress field to be computed
    progress = fields.Float('Progress (%)', 
                          digits=(5, 2),
                          compute='_compute_progress',
                          store=True,
                          help="Auto-calculated progress: (Actual / Target) * 100")
    
    # Replace the weightage field with these new fields
    available_weightage = fields.Float(
        'Available Weightage (%)', 
        compute='_compute_available_weightage',
        store=True,
        digits=(5, 2),
        help="Available weightage budget for the selected team"
    )

    distributed_weightage = fields.Float(
        'Distributed Weightage (%)',
        digits=(5, 2),
        default=0.0,
        help="Weightage allocated to this objective breakdown"
    )

    remaining_weightage = fields.Float(
        'Remaining Weightage (%)',
        compute='_compute_remaining_weightage',
        store=True,
        digits=(5, 2),
        help="Remaining weightage available for distribution"
    )


    # data_source = fields.Selection([
    #     ('manual', 'Manual Entry'),
    #     ('jira', 'Jira'),
    #     ('github', 'Github'),
    #     ('lms', 'LMS')
    # ], string='Data Source', default='manual', required=True)

    # Display fields for better UX
    target_display = fields.Char('Target', compute='_compute_target_display', store=True)
    actual_display = fields.Char('Actual', compute='_compute_actual_display', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure result_type is set based on context"""
        for vals in vals_list:
            if not vals.get('result_type'):
                if self.env.context.get('weightage_type') == 'role':
                    vals['result_type'] = 'role'
                elif self.env.context.get('weightage_type') == 'common':
                    vals['result_type'] = 'common'
                else:
                    vals['result_type'] = 'department'
        return super().create(vals_list)

    @api.onchange('okr_template_id')
    def _onchange_okr_template(self):
        """Update team domain when template changes"""
        if self.okr_template_id:
            return {
                'domain': {
                    'team_id': [
                        ('company_id', '=', self.okr_template_id.company_id.id),
                        ('department_id', '=', self.okr_template_id.department_id.id)
                    ]
                }
            }
        return {'domain': {'team_id': []}}

    @api.depends('team_id', 'okr_template_id.weightage_ids', 
                'okr_template_id.weightage_ids.department_weightage',
                'okr_template_id.weightage_ids.role_weightage',
                'okr_template_id.weightage_ids.common_weightage',
                'result_type')
    def _compute_available_weightage(self):
        """Compute total available weightage for the selected team"""
        for record in self:
            if record.team_id and record.okr_template_id:
                weightage_record = record.okr_template_id.weightage_ids.filtered(
                    lambda w: w.team_id == record.team_id
                )
                if weightage_record:
                    if record.result_type == 'role':
                        record.available_weightage = weightage_record[0].role_weightage
                    elif record.result_type == 'common':
                        record.available_weightage = weightage_record[0].common_weightage
                    else:  # department
                        record.available_weightage = weightage_record[0].department_weightage
                else:
                    record.available_weightage = 0.0
            else:
                record.available_weightage = 0.0

    @api.depends('team_id', 'available_weightage', 'distributed_weightage',
                'okr_template_id.department_key_result_ids.distributed_weightage',
                'okr_template_id.role_key_result_ids.distributed_weightage',
                'okr_template_id.common_key_result_ids.distributed_weightage')
    def _compute_remaining_weightage(self):
        """Compute remaining weightage available for distribution"""
        for record in self:
            if record.team_id and record.available_weightage > 0:
                # Get all records for this team and type
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type),
                    ('id', '!=', record._origin.id)  # Exclude current record
                ]
                related_records = self.search(domain)
                total_distributed = sum(related_records.mapped('distributed_weightage'))
                record.remaining_weightage = max(0, record.available_weightage - total_distributed)
            else:
                record.remaining_weightage = 0.0

    @api.constrains('distributed_weightage', 'team_id')
    def _check_distributed_weightage(self):
        """Validate weightage distribution"""
        for record in self:
            if record.distributed_weightage < 0:
                raise ValidationError(_("Distributed weightage cannot be negative."))
            
            if record.team_id and record.distributed_weightage > 0:
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type)
                ]
                related_records = self.search(domain)
                total_distributed = sum(related_records.mapped('distributed_weightage'))
                
                if total_distributed > record.available_weightage:
                    raise ValidationError(_(
                        "Total distributed weightage (%.2f%%) exceeds available weightage (%.2f%%) for team %s"
                    ) % (total_distributed, record.available_weightage, record.team_id.name))

    
    @api.constrains('distributed_weightage', 'team_id', 'result_type')
    def _check_total_distributed_weightage(self):
        """Ensure total distributed weightage doesn't exceed available budget"""
        for record in self:
            if record.team_id and record.distributed_weightage > 0:
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type)
                ]
                all_records = self.search(domain)
                total_distributed = sum(all_records.mapped('distributed_weightage'))
                
                if total_distributed > record.available_weightage:
                    raise ValidationError(_(
                        "Total distributed weightage (%.2f%%) for %s objectives cannot exceed "
                        "the available weightage (%.2f%%) for team %s"
                    ) % (
                        total_distributed,
                        dict(self._fields['result_type'].selection).get(record.result_type),
                        record.available_weightage,
                        record.team_id.name
                    ))


    @api.onchange('distributed_weightage')
    def _onchange_distributed_weightage(self):
        """Show warning when approaching available weightage limit"""
        if self.team_id and self.distributed_weightage > 0:
            domain = [
                ('okr_template_id', '=', self.okr_template_id.id),
                ('team_id', '=', self.team_id.id),
                ('result_type', '=', self.result_type),
                ('id', '!=', self._origin.id)
            ]
            other_records = self.search(domain)
            total_distributed = sum(other_records.mapped('distributed_weightage')) + self.distributed_weightage
            
            if total_distributed > self.available_weightage:
                excess = total_distributed - self.available_weightage
                return {
                    'warning': {
                        'title': _('Weightage Distribution Warning'),
                        'message': _(
                            "Current distribution exceeds available weightage by %.2f%%.\n"
                            "Available: %.2f%%\n"
                            "Total Distributed: %.2f%%"
                        ) % (excess, self.available_weightage, total_distributed)
                    }
                }

    @api.onchange('team_id')
    def _onchange_team_id(self):
        """Reset distributed weightage when team changes"""
        self.distributed_weightage = 0.0
        # Update available weightage
        if self.team_id and self.okr_template_id:
            weightage_record = self.okr_template_id.weightage_ids.filtered(
                lambda w: w.team_id == self.team_id
            )
            if weightage_record:
                if self.result_type == 'role':
                    self.available_weightage = weightage_record[0].role_weightage
                elif self.result_type == 'common':
                    self.available_weightage = weightage_record[0].common_weightage
                else:  # department
                    self.available_weightage = weightage_record[0].department_weightage


    @api.depends('actual_value', 'target_value')
    def _compute_progress(self):
        """
        Compute progress percentage based on actual and target values
        Formula: (Actual / Target) * 100
        """
        for record in self:
            if record.target_value and record.target_value != 0:
                try:
                    progress = (record.actual_value / record.target_value) * 100
                    # Round to 2 decimal places and ensure it doesn't exceed 100%
                    record.progress = min(round(progress, 2), 100)
                except (ZeroDivisionError, TypeError):
                    record.progress = 0.0
            else:
                record.progress = 0.0

    @api.onchange('actual_value', 'target_value')
    def _onchange_values(self):
        """Trigger progress recalculation when values change"""
        if self.target_value and self.target_value != 0:
            try:
                progress = (self.actual_value / self.target_value) * 100
                self.progress = min(round(progress, 2), 100)
            except (ZeroDivisionError, TypeError):
                self.progress = 0.0
        else:
            self.progress = 0.0

    # Add validation constraints
    @api.constrains('target_value')
    def _check_target_value(self):
        for record in self:
            if record.target_value <= 0:
                raise ValidationError(_("Target value must be greater than zero."))

    @api.constrains('actual_value')
    def _check_actual_value(self):
        for record in self:
            if record.actual_value < 0:
                raise ValidationError(_("Actual value cannot be negative."))


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

            

    
class OHAppraisalObjectiveBreakdown(models.Model):
    _name = 'oh.appraisal.objective.breakdown'
    _description = 'Objective Breakdown Items'
    _order = 'sequence, id'
    _rec_name = 'objective_item'

    sequence = fields.Integer('Sequence', default=10)
    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     string='OKR Template',
                                     required=True, 
                                     ondelete='cascade')
    objective_item = fields.Char('Objective Item', 
                                required=True,
                                help="Individual objective breakdown item")
    priority = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], string='Priority', 
       default='high', 
    #    required=True, 
       help="Priority level of this objective")
    # created_by = fields.Char('Created By', 
    #                         readonly=True,
    #                         default=lambda self: self.env.user.login)
    # created_datetime = fields.Datetime('Created On',
    #                                  readonly=True,
    #                                  default=lambda self: fields.Datetime.now())