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

    name = fields.Char('Template Name', required=True, tracking=True)
    goal = fields.Char('Goal', tracking=True, required=True, help="Overall goal of this OKR template")
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company,
                                domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])
    
    description = fields.Html('Description')
    
    # Objective Section
    objective_title_department = fields.Char(
        'Department Objective', 
        tracking=True,
        required=True,
        help="Department specific objective"
    )
    objective_breakdown_department_ids = fields.One2many(
        'oh.appraisal.objective.breakdown',
        'okr_template_id',
        string='Department Objective Breakdowns',
        domain=[('breakdown_type', '=', 'department')],
        context={'default_breakdown_type': 'department'}
    )

    objective_title_role = fields.Char(
        'Role Objective', 
        tracking=True,
        required=True,
        help="Role specific objective"
    )
    objective_breakdown_role_ids = fields.One2many(
        'oh.appraisal.objective.breakdown',
        'okr_template_id',
        string='Role Objective Breakdowns',
        domain=[('breakdown_type', '=', 'role')],
        context={'default_breakdown_type': 'role'}
    )

    objective_title_common = fields.Char(
        'Common Objective', 
        tracking=True,
        required=True,
        help="Common specific objective"
    )
    objective_breakdown_common_ids = fields.One2many(
        'oh.appraisal.objective.breakdown',
        'okr_template_id',
        string='Common Objective Breakdowns',
        domain=[('breakdown_type', '=', 'common')],
        context={'default_breakdown_type': 'common'}
    )

    # Keep original fields for backward compatibility
    objective_title = fields.Char('Legacy Objective Title', tracking=True)
    objective_breakdown_ids = fields.One2many(
        'oh.appraisal.objective.breakdown',
        'okr_template_id',
        string='Legacy Objective Breakdowns'
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
        index=True,
        domain="[('company_id', '=', company_id)]",
        tracking=True,
        required=True,
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

    key_result_count = fields.Integer('Key Results Count', 
                                    compute='_compute_key_result_count')

    
    department_distributed_total = fields.Float(
        compute='_compute_distributed_totals',
        store=True,
        digits=(5, 2)
    )
    role_distributed_total = fields.Float(
        compute='_compute_distributed_totals',
        store=True,
        digits=(5, 2)
    )
    common_distributed_total = fields.Float(
        compute='_compute_distributed_totals',
        store=True,
        digits=(5, 2)
    )

    selected_teams_display = fields.Char(
        string='Selected Teams',
        compute='_compute_selected_teams_display',
        store=True,
        help="Teams selected in objective weightage"
    )

    _sql_constraints = [
        ('unique_name_per_department',
         'unique(name, department_id)',
         'Template name must be unique per department!')
    ]

    @api.constrains('name', 'department_id')
    def _check_unique_name_per_department(self):
        for record in self:
            if record.name and record.department_id:
                domain = [
                    ('name', '=', record.name),
                    ('department_id', '=', record.department_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain):
                    raise ValidationError(_(
                        'A template with the name "%s" already exists for department "%s"'
                    ) % (record.name, record.department_id.name))
    
    def action_open_master_template(self):
        """Opens Master Template dashboard with department pre-selected"""
        self.ensure_one()
        
        if not self.department_id:
            return False

        # Return the dashboard action with department context
        return {
            'type': 'ir.actions.client',
            'tag': 'oh_appraisal_dashboard',
            'name': f'Department Weightage - {self.department_id.name}',
            'context': {
                'default_department_id': self.department_id.id,
                'default_company_id': self.company_id.id,
            },
            'target': 'current',
        }

    @api.depends('weightage_ids', 'weightage_ids.team_id')
    def _compute_selected_teams_display(self):
        """Compute display string for selected teams"""
        for record in self:
            teams = record.weightage_ids.mapped('team_id')
            if teams:
                record.selected_teams_display = ', '.join(teams.mapped('name'))
            else:
                record.selected_teams_display = ''
    
    @api.depends('department_key_result_ids.distributed_weightage',
                'role_key_result_ids.distributed_weightage',
                'common_key_result_ids.distributed_weightage')
    def _compute_distributed_totals(self):
        for record in self:
            record.department_distributed_total = sum(
                record.department_key_result_ids.mapped('distributed_weightage')
            )
            record.role_distributed_total = sum(
                record.role_key_result_ids.mapped('distributed_weightage')
            )
            record.common_distributed_total = sum(
                record.common_key_result_ids.mapped('distributed_weightage')
            )

    @api.constrains('department_distributed_total', 'role_distributed_total', 'common_distributed_total')
    def _check_distributed_totals(self):
        for record in self:
            if record.department_distributed_total > record.department_budget_functional:
                raise ValidationError(_(
                    "Total distributed department weightage (%.2f%%) cannot exceed "
                    "available budget (%.2f%%)"
                ) % (record.department_distributed_total, record.department_budget_functional))
            
            if record.role_distributed_total > record.department_budget_role:
                raise ValidationError(_(
                    "Total distributed role weightage (%.2f%%) cannot exceed "
                    "available budget (%.2f%%)"
                ) % (record.role_distributed_total, record.department_budget_role))
            
            if record.common_distributed_total > record.department_budget_common:
                raise ValidationError(_(
                    "Total distributed common weightage (%.2f%%) cannot exceed "
                    "available budget (%.2f%%)"
                ) % (record.common_distributed_total, record.department_budget_common))

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
        domain="[('okr_template_id', '=', okr_template_id), ('breakdown_type', '=', result_type)]"
    )

    breakdown_priority = fields.Selection(
        related='key_objective_breakdown.priority',
        string='Priority',
        store=True,
        readonly=True
    )
    
    metric = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('count', 'Count (Numeric)'),
        ('rating', 'Rating (Scale)'),
        ('score', 'Score (Points)')
    ], string='Metric/Measure', default=False,  # Changed from False to ''
    help="Select the type of measurement:\n"
        "• Percentage: Measured as percentage value (0-100%)\n"
        "• Count: Numeric count or quantity\n"
        "• Rating: Scale-based rating (e.g., 1-5, 1-10)\n"
        "• Score: Points-based scoring system\n"
        "• Leave blank if no specific metric applies\n"
        "• So, for any non-numerical value, use the blank option; else all values should be numeric.")
    
    # Target Value fields
    target_operator = fields.Selection([
        ('eq', '='),
        ('ne', '≠'),
        ('gt', '>'),
        ('lt', '<'),
        ('gte', '≥'),
        ('lte', '≤')
    ], string='Target Operator', default='gte',
    help="Comparison operator for target achievement:\n"
         "• = (Equal): Exact value required\n"
         "• ≠ (Not Equal): Any value except specified\n"
         "• > (Greater): Above specified value\n"
         "• < (Less): Below specified value\n"
         "• ≥ (Greater/Equal): At or above specified\n"
         "• ≤ (Less/Equal): At or below specified")
    target_value = fields.Float('Target Value', required=True,
    help="Target numeric value to be achieved")
    target_unit = fields.Char('Target Unit', 
    help="Unit of measurement (e.g., units, sales, rejections, hours)")
    target_period = fields.Char('Target Period', 
    help="Time period for target (e.g., in Q1, per month, annually)")
    
    # Actual Value fields
    actual_operator = fields.Selection([
        ('eq', '='),
        ('ne', '≠'),
        ('gt', '>'),
        ('lt', '<'),
        ('gte', '≥'),
        ('lte', '≤')
    ], string='Actual Operator', default='gte',
    help="Comparison operator for actual achievement:\n"
         "• = (Equal): Exact value achieved\n"
         "• ≠ (Not Equal): Any value except specified\n"
         "• > (Greater): Exceeded specified value\n"
         "• < (Less): Below specified value\n"
         "• ≥ (Greater/Equal): At or above specified\n"
         "• ≤ (Less/Equal): At or below specified")
    actual_value = fields.Float('Actual Value',
    help="Actual numeric value achieved/measured")
    actual_unit = fields.Char('Actual Unit',
    help="Unit of actual measurement")
    actual_period = fields.Char('Actual Period',
    help="Time period for actual measurement")
    
    # Achievement field (replacing progress)
    # achieve = fields.Char('Achieve',
    # help="Achievement status or assessment (To be configured)",
    # default='')
    
    # Weightage fields
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
        help="Weightage allocated to this objective breakdown")

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
            'okr_template_id.allocated_functional',
            'okr_template_id.allocated_role',
            'okr_template_id.allocated_common',
            'result_type')
    def _compute_available_weightage(self):
        """Compute available weightage based on allocated weightages"""
        for record in self:
            if record.team_id and record.okr_template_id:
                # Get allocated weightage based on type
                if record.result_type == 'role':
                    total_available = record.okr_template_id.allocated_role
                elif record.result_type == 'common':
                    total_available = record.okr_template_id.allocated_common
                else:  # department
                    total_available = record.okr_template_id.allocated_functional

                # Get already distributed amount for this team
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type),
                    ('id', '!=', record.id)
                ]
                other_records = self.search(domain)
                total_distributed = sum(other_records.mapped('distributed_weightage'))
                
                # Set available as remaining amount
                record.available_weightage = max(0, total_available - total_distributed)
            else:
                record.available_weightage = 0.0

    @api.constrains('distributed_weightage', 'team_id', 'result_type')
    def _check_distributed_weightage(self):
        """Validate distributed weightage against allocated budget"""
        for record in self:
            if record.distributed_weightage < 0:
                raise ValidationError(_("Distributed weightage cannot be negative."))
            
            if record.team_id and record.distributed_weightage > 0:
                # Get all records for this team and type
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type)
                ]
                all_records = self.search(domain)
                total_distributed = sum(all_records.mapped('distributed_weightage'))
                
                # Get allocated budget based on type
                if record.result_type == 'role':
                    allocated_budget = record.okr_template_id.allocated_role
                elif record.result_type == 'common':
                    allocated_budget = record.okr_template_id.allocated_common
                else:  # department
                    allocated_budget = record.okr_template_id.allocated_functional
                
                if total_distributed > allocated_budget:
                    raise ValidationError(_(
                        "Total distributed weightage (%.2f%%) for %s objectives cannot exceed "
                        "the allocated weightage (%.2f%%)"
                    ) % (
                        total_distributed,
                        dict(record._fields['result_type'].selection).get(record.result_type),
                        allocated_budget
                    ))

    @api.constrains('distributed_weightage', 'team_id', 'result_type')
    def _check_total_distributed_weightage(self):
        """Ensure total distributed weightage doesn't exceed allocated budget"""
        for record in self:
            if record.team_id and record.distributed_weightage > 0:
                domain = [
                    ('okr_template_id', '=', record.okr_template_id.id),
                    ('team_id', '=', record.team_id.id),
                    ('result_type', '=', record.result_type)
                ]
                all_records = self.search(domain)
                total_distributed = sum(all_records.mapped('distributed_weightage'))
                
                # Get allocated budget based on type
                if record.result_type == 'role':
                    allocated_budget = record.okr_template_id.allocated_role
                elif record.result_type == 'common':
                    allocated_budget = record.okr_template_id.allocated_common
                else:  # department
                    allocated_budget = record.okr_template_id.allocated_functional
                
                if total_distributed > allocated_budget:
                    raise ValidationError(_(
                        "Total distributed weightage (%.2f%%) for %s objectives cannot exceed "
                        "the allocated weightage (%.2f%%)"
                    ) % (
                        total_distributed,
                        dict(record._fields['result_type'].selection).get(record.result_type),
                        allocated_budget
                    ))

    @api.onchange('distributed_weightage')
    def _onchange_distributed_weightage(self):
        """Show warning when approaching allocated budget"""
        if self.team_id and self.distributed_weightage > 0:
            # Get total distributed for this team and type
            domain = [
                ('okr_template_id', '=', self.okr_template_id.id),
                ('team_id', '=', self.team_id.id),
                ('result_type', '=', self.result_type),
                ('id', '!=', self._origin.id)
            ]
            other_records = self.search(domain)
            total_distributed = sum(other_records.mapped('distributed_weightage')) + self.distributed_weightage
            
            # Get allocated budget based on type
            if self.result_type == 'role':
                allocated_budget = self.okr_template_id.allocated_role
            elif self.result_type == 'common':
                allocated_budget = self.okr_template_id.allocated_common
            else:  # department
                allocated_budget = self.okr_template_id.allocated_functional
            
            if total_distributed > allocated_budget:
                return {
                    'warning': {
                        'title': _('Weightage Distribution Warning'),
                        'message': _(
                            "Total distributed weightage (%.2f%%) exceeds allocated budget (%.2f%%)"
                        ) % (total_distributed, allocated_budget)
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

    @api.onchange('okr_template_id', 'result_type')
    def _onchange_template_and_type(self):
        """Update domain for key_objective_breakdown when template or type changes"""
        self.key_objective_breakdown = False  # Clear existing selection
        if self.okr_template_id and self.result_type:
            return {
                'domain': {
                    'key_objective_breakdown': [
                        ('okr_template_id', '=', self.okr_template_id.id),
                        ('breakdown_type', '=', self.result_type)
                    ]
                }
            }
        return {'domain': {'key_objective_breakdown': []}}

    @api.constrains('key_objective_breakdown', 'result_type')
    def _check_breakdown_type_match(self):
        """Ensure breakdown type matches the result type"""
        for record in self:
            if record.key_objective_breakdown and record.key_objective_breakdown.breakdown_type != record.result_type:
                raise ValidationError(_(
                    "Selected objective breakdown type (%s) does not match the key result type (%s)"
                ) % (
                    dict(record.key_objective_breakdown._fields['breakdown_type'].selection).get(
                        record.key_objective_breakdown.breakdown_type
                    ),
                    dict(record._fields['result_type'].selection).get(record.result_type)
                ))

    @api.onchange('metric')
    def _onchange_metric(self):
        """Set default descriptions based on selected metric"""
        metric_descriptions = {
            'percentage': 'Measured as percentage (0-100%)',
            'count': 'Measured as numeric count/quantity',
            'rating': 'Measured on a rating scale',
            'score': 'Measured in points'
        }
        
        if self.metric and self.metric in metric_descriptions:  # This checks for non-empty string
            if not self.target_unit:
                self.target_unit = metric_descriptions[self.metric]

    
class OHAppraisalObjectiveBreakdown(models.Model):
    _name = 'oh.appraisal.objective.breakdown'
    _description = 'Objective Breakdown Items'
    _order = 'sequence, id'
    _rec_name = 'objective_item'

    breakdown_type = fields.Selection([
        ('department', 'Department'),
        ('role', 'Role'),
        ('common', 'Common')
    ], string='Breakdown Type', required=True, default='department')

    sequence = fields.Integer('Sequence', default=10)
    okr_template_id = fields.Many2one('oh.appraisal.okr.template', 
                                     string='OKR Template',
                                     required=True, 
                                     ondelete='cascade')
    objective_item = fields.Char('Objective Parameter', 
                                required=True,
                                help="Individual objective breakdown parameter")
    priority = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], string='Priority', 
       default='high',
       help="Priority level of this objective")

    @api.model_create_multi
    def create(self, vals_list):
        """Set breakdown type from context if not specified"""
        for vals in vals_list:
            if not vals.get('breakdown_type'):
                if self.env.context.get('default_breakdown_type'):
                    vals['breakdown_type'] = self.env.context['default_breakdown_type']
        return super().create(vals_list)