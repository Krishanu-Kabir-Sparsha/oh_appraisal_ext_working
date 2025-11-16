# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OHAppraisalTeam(models.Model):
    _name = 'oh.appraisal.team'
    _description = 'Appraisal Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, parent_path'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'

    # ============ Basic Information ============
    name = fields.Char('Team Name', required=True, tracking=True)
    code = fields.Char('Team Code', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    color = fields.Integer('Color Index', default=0)
    
    # ============ Hierarchy ============
    parent_id = fields.Many2one(
        'oh.appraisal.team', 
        'Parent Team', 
        index=True, 
        ondelete='cascade',
        tracking=True,
        domain="[('company_id', '=', company_id), ('department_id', '=', department_id), ('id', '!=', id)]"
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('oh.appraisal.team', 'parent_id', 'Sub Teams')
    child_count = fields.Integer('Sub Team Count', compute='_compute_child_count', store=True)
    
    complete_name = fields.Char(
        'Complete Name', 
        compute='_compute_complete_name',
        recursive=True, 
        store=True
    )
    
    # ============ Organization ============
    company_id = fields.Many2one(
        'res.company', 
        'Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department', 
        'Department',
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    # ============ Team Members ============
    team_leader_id = fields.Many2one(
        'hr.employee',
        'Team Leader',
        tracking=True,
        domain="[('company_id', '=', company_id), ('department_id', '=', department_id)]",
        help="Primary leader of this team"
    )
    
    member_ids = fields.Many2many(
        'hr.employee', 
        'oh_appraisal_team_employee_rel', 
        'team_id', 
        'employee_id',
        string='Team Members',
        domain="[('company_id', '=', company_id), ('department_id', '=', department_id)]"
    )
    
    member_count = fields.Integer('Member Count', compute='_compute_member_count', store=True)
    
    # ============ Team Type ============
    team_type = fields.Selection([
        ('functional', 'Functional Team'),
        ('cross_functional', 'Cross-Functional Team'),
        ('project', 'Project Team'),
        ('department', 'Department Team')
    ], string='Team Type', default='functional', tracking=True)
    
    # ============ Additional Info ============
    description = fields.Html('Description')
    notes = fields.Text('Internal Notes')
    
    # ============ SQL Constraints ============
    _sql_constraints = [
        ('name_company_dept_uniq', 
         'unique(name, company_id, department_id, parent_id)', 
         'A team with this name already exists in this department!'),
        ('code_company_uniq',
         'unique(code, company_id)',
         'Team code must be unique per company!')
    ]

    # ============ Compute Methods ============
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete hierarchical name"""
        for team in self:
            if team.parent_id:
                team.complete_name = f"{team.parent_id.complete_name} / {team.name}"
            else:
                team.complete_name = team.name

    @api.depends('child_ids')
    def _compute_child_count(self):
        """Count direct child teams"""
        for team in self:
            team.child_count = len(team.child_ids)

    @api.depends('member_ids')
    def _compute_member_count(self):
        """Count direct team members"""
        for team in self:
            team.member_count = len(team.member_ids)

    # ============ Onchange Methods ============
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Update domains when company changes"""
        if self.company_id:
            if self.department_id and self.department_id.company_id != self.company_id:
                self.department_id = False
            if self.parent_id and self.parent_id.company_id != self.company_id:
                self.parent_id = False
            self.member_ids = False
            self.team_leader_id = False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Update member domains when department changes"""
        self.member_ids = False
        self.team_leader_id = False
        if self.parent_id and self.parent_id.department_id != self.department_id:
            self.parent_id = False

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        """Inherit company and department from parent if not set"""
        if self.parent_id:
            if not self.company_id:
                self.company_id = self.parent_id.company_id
            if not self.department_id:
                self.department_id = self.parent_id.department_id

    @api.onchange('member_ids')
    def _onchange_member_ids(self):
        """Auto-add team leader if not in members"""
        if self.team_leader_id and self.team_leader_id not in self.member_ids:
            self.member_ids = [(4, self.team_leader_id.id)]

    # ============ Constraints ============
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Prevent circular parent relationships"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive team hierarchies!'))

    @api.constrains('team_leader_id', 'member_ids')
    def _check_leader_in_members(self):
        """Ensure team leader is in team members"""
        for team in self:
            if team.team_leader_id and team.member_ids and team.team_leader_id not in team.member_ids:
                raise ValidationError(_(
                    'Team leader "%s" must be in team members! Please add the leader to the team first.'
                ) % team.team_leader_id.name)

    # ============ Action Methods ============
    def action_view_members(self):
        """View team members"""
        self.ensure_one()
        return {
            'name': _('Team Members - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.member_ids.ids)],
            'context': {'default_department_id': self.department_id.id}
        }

    def action_view_sub_teams(self):
        """View sub-teams"""
        self.ensure_one()
        return {
            'name': _('Sub Teams - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'oh.appraisal.team',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_company_id': self.company_id.id,
                'default_department_id': self.department_id.id
            }
        }

    def action_create_sub_team(self):
        """Create a sub-team"""
        self.ensure_one()
        return {
            'name': _('Create Sub Team'),
            'type': 'ir.actions.act_window',
            'res_model': 'oh.appraisal.team',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_parent_id': self.id,
                'default_company_id': self.company_id.id,
                'default_department_id': self.department_id.id
            }
        }

    # ============ Name Methods ============
    def name_get(self):
        """Display complete hierarchical name"""
        return [(team.id, team.complete_name or team.name) for team in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Search by name or complete_name"""
        args = args or []
        if name:
            teams = self._search([('complete_name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
            if not teams:
                teams = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            teams = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return teams