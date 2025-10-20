# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import logging
_logger = logging.getLogger(__name__)

class OHAppraisalMaster(models.Model):
    _name = 'oh.appraisal.master'
    _description = 'Appraisal Master Control (Weightages & Engine)'
    _rec_name = 'name'

    name = fields.Char(required=True, help="Name of the master configuration (e.g., 'Sales Annual 2025').")
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', help="Company this master belongs to. Leave blank for global usage.")
    description = fields.Text(help="Optional notes and documentation for administrators.")

    # Optional metadata to help users choose configurations
    industry_type = fields.Many2one('oh.appraisal.industry', string="Industry Type", 
                               help="Select your industry type for appraisal context")

    assessment_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], string="Assessment Period", help="Define how often appraisals are conducted.")

    
    # Template links (no defaults)
    master_template_id = fields.Many2one('oh.appraisal.template', domain=[('template_type','=','master')], string='Master Template', help="Optional master template that may include top-level KPIs.")
    department_template_ids = fields.Many2many('oh.appraisal.template', 'oh_app_master_department_rel', 'master_id','template_id', domain=[('template_type','=','department')], string='Department Templates', help="Department-level templates. Admins select relevant templates here.")
    role_template_ids = fields.Many2many('oh.appraisal.template', 'oh_app_master_role_rel', 'master_id','template_id', domain=[('template_type','=','role')], string='Role Templates', help="Role-based templates for specific jobs.")
    common_template_ids = fields.Many2many('oh.appraisal.template', 'oh_app_master_common_rel', 'master_id','template_id', domain=[('template_type','=','common')], string='Common Templates', help="Org-wide common templates that apply to all employees (e.g., company values).")

    # Category weightages (no default — admin must set to distribute 100%)
    weight_functional = fields.Float(string='Functional (Dept) %', required=True, help="Percentage weight for department/functional items. Must sum with other category weights to 100.")
    weight_role = fields.Float(string='Role %', required=True, help="Percentage weight for role-based items.")
    weight_common = fields.Float(string='Common %', required=True, help="Percentage weight for common/org-wide items.")

    # Scoring & assessment framework (no defaults)
    scoring_template_id = fields.Many2one('oh.appraisal.scoring', string='Scoring Scale', help="Select the scoring scale to interpret raw numeric answers (map them to percent & labels).")
    assessment_framework_id = fields.Many2one('oh.appraisal.framework', string='Assessment Framework', help="Reviewer weight distribution (used when answers include reviewer breakdowns).")

    # UI simulation snapshot
    last_sim_result = fields.Text(string='Last Simulation (JSON)', readonly=True, help="JSON snapshot of the last simulation run for quick preview.")
    last_sim_final_percentage = fields.Float(string='Last Sim Final %', digits=(6,2), readonly=True)
    last_sim_rating = fields.Char(string='Last Sim Rating', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'A master config with this name already exists for the company.')
    ]

    @api.constrains('weight_functional','weight_role','weight_common')
    def _check_weights_sum(self):
        for rec in self:
            # Ensure admin sets meaningful weights that sum to 100
            wf = (rec.weight_functional or 0.0)
            wr = (rec.weight_role or 0.0)
            wc = (rec.weight_common or 0.0)
            total = wf + wr + wc
            if abs(total - 100.0) > 0.001:
                raise ValidationError(_("Functional + Role + Common weightages must sum to 100%% (got %s). Please set the three weights appropriately.") % (total,))

    # ------------- Helper utilities --------------
    def _gather_template_lines(self, templates):
        """
        Build mapping of template items by code -> metadata:
        { code: {'name':..., 'max_score':..., 'template_id': id, 'template_type': ..., 'weight': ...} }
        """
        lines = {}
        for tmpl in templates:
            for ln in tmpl.line_ids:
                code = (ln.code or ln.name or str(ln.id)).strip()
                if not code:
                    code = str(ln.id)
                lines[code] = {
                    'name': ln.name,
                    'max_score': float(ln.max_score or 0.0),
                    'template_id': tmpl.id,
                    'template_type': tmpl.template_type,
                    'weight': float(ln.weight or 1.0),
                }
        return lines

    def get_templates_for_employee(self, employee):
        """
        Choose best-matching templates for an employee:
         - department template: match by department_id if available else first department template
         - role template: match by job_id if available else first role template
         - common templates: return all configured common templates
        Returns tuple (dept_template, role_template, common_templates_recordset)
        """
        if not employee:
            return (None, None, self.common_template_ids or self.env['oh.appraisal.template'].browse([]))

        dept_template = None
        role_template = None
        if employee.department_id:
            dept_template = (self.department_template_ids.filtered(lambda t: t.department_id == employee.department_id)[:1] or self.department_template_ids[:1])
            if isinstance(dept_template, list):
                dept_template = dept_template[0] if dept_template else None
        if employee.job_id:
            role_template = (self.role_template_ids.filtered(lambda t: t.job_id == employee.job_id)[:1] or self.role_template_ids[:1])
            if isinstance(role_template, list):
                role_template = role_template[0] if role_template else None

        return (dept_template, role_template, (self.common_template_ids or self.env['oh.appraisal.template'].browse([])))

    # ------------- Core scoring pipeline --------------
    def compute_employee_score(self, employee, answers_by_item=None, template_selection=None):
        """
        Compute the final appraisal for an employee based on:
         - selected templates (department/role/common),
         - per-item answers (numeric or reviewer split),
         - scoring scale and assessment framework.

        answers_by_item: dict {item_code: numeric_or_reviewer_dict}
            numeric example: {"teamwork": 4}
            reviewer dict example: {"teamwork": {"self":4, "peer":3.5, "manager":4.2}}

        template_selection: optional dict: {'department': id, 'role': id, 'common': [ids]}

        Returns comprehensive dict with breakdowns and final percentage.
        """
        self.ensure_one()
        answers = dict(answers_by_item or {})

        # choose templates (explicit selection takes precedence)
        if template_selection:
            dept = self.env['oh.appraisal.template'].browse(template_selection.get('department')) if template_selection.get('department') else None
            role = self.env['oh.appraisal.template'].browse(template_selection.get('role')) if template_selection.get('role') else None
            common_templates = self.env['oh.appraisal.template'].browse(template_selection.get('common')) if template_selection.get('common') else (self.common_template_ids or self.env['oh.appraisal.template'].browse([]))
        else:
            dept, role, common_templates = self.get_templates_for_employee(employee)

        func_lines = self._gather_template_lines(dept and self.env['oh.appraisal.template'].browse(dept.id) or self.env['oh.appraisal.template'].browse([]))
        role_lines = self._gather_template_lines(role and self.env['oh.appraisal.template'].browse(role.id) or self.env['oh.appraisal.template'].browse([]))
        common_lines = self._gather_template_lines(common_templates)

        scoring = self.scoring_template_id or (self.env['oh.appraisal.scoring'].search([], limit=1))

        def _compute_item_percent(code, meta, value):
            """
            Compute percent (0..100) for a single item given raw value(s).
            - If value is a dict of reviewer_type->score and assessment framework is present,
              use framework to aggregate to single raw value.
            - If scoring template is present, interpret raw as scoring scale and normalize.
            - Else fallback to max_score on template line.
            """
            # resolve raw value
            raw = 0.0
            if isinstance(value, dict) and self.assessment_framework_id:
                # pass the dict to framework aggregator (it expects reviewer_type->value)
                try:
                    raw = float(self.assessment_framework_id.compute_aggregate(value) or 0.0)
                except Exception:
                    raw = 0.0
            else:
                # numeric (or None)
                try:
                    raw = float(value if value not in (None, '') else 0.0)
                except Exception:
                    raw = 0.0

            # compute percent
            if scoring and scoring.exists():
                p = scoring.normalize_to_percent(raw)
            else:
                max_score = float(meta.get('max_score') or 0.0)
                p = (raw / max_score) * 100.0 if max_score > 0 else 0.0
            return round(p, 2), raw

        def aggregate_category(lines_map):
            total_weight = 0.0
            weighted_sum = 0.0
            items = {}
            for code, meta in lines_map.items():
                val = answers.get(code)
                pct, raw_value = _compute_item_percent(code, meta, val)
                w = float(meta.get('weight') or 1.0)
                weighted_sum += (pct * w)
                total_weight += w
                items[code] = {
                    'name': meta.get('name'),
                    'percent': pct,
                    'raw': raw_value,
                    'max': meta.get('max_score'),
                    'weight': w,
                    'template_id': meta.get('template_id'),
                }
            category_percent = round((weighted_sum / total_weight) if total_weight else 0.0, 2)
            return {'percent': category_percent, 'items': items, 'total_weight': total_weight}

        func_res = aggregate_category(func_lines)
        role_res = aggregate_category(role_lines)
        common_res = aggregate_category(common_lines)

        wf = (self.weight_functional or 0.0) / 100.0
        wr = (self.weight_role or 0.0) / 100.0
        wc = (self.weight_common or 0.0) / 100.0

        final_percent = round((func_res['percent'] * wf) + (role_res['percent'] * wr) + (common_res['percent'] * wc), 2)

        final_raw_on_scale = None
        rating_label = ''
        if scoring and scoring.exists():
            final_raw_on_scale = (final_percent / 100.0) * (scoring.scale_max - scoring.scale_min) + scoring.scale_min
            rating_label = scoring.to_label(final_raw_on_scale) or ''
        else:
            # fallback descriptive thresholds (only used if no scoring lines exist)
            if final_percent >= 90:
                rating_label = 'Outstanding'
            elif final_percent >= 75:
                rating_label = 'Exceeds'
            elif final_percent >= 60:
                rating_label = 'Meets'
            else:
                rating_label = 'Needs Improvement'

        return {
            'employee_id': employee.id if employee else False,
            'templates': {
                'department': dept.id if dept else False,
                'role': role.id if role else False,
                'common': [t.id for t in (common_templates or [])] if common_templates else []
            },
            'functional': func_res,
            'role': role_res,
            'common': common_res,
            'weights': {'functional': self.weight_functional, 'role': self.weight_role, 'common': self.weight_common},
            'final_percentage': final_percent,
            'final_raw_on_scale': round(final_raw_on_scale,4) if final_raw_on_scale is not None else None,
            'rating_label': rating_label,
            'scoring_id': scoring.id if scoring else False,
            'explanation': {
                'note': 'Dynamic scoring computed via templates, per-item weights and optional reviewer-framework aggregation.'
            }
        }

    def action_run_simulation(self, employee_id=None, answers_by_item=None):
        self.ensure_one()
        emp = self.env['hr.employee'].browse(employee_id) if employee_id else None
        comp = self.compute_employee_score(emp, answers_by_item=answers_by_item or {})
        try:
            self.last_sim_result = json.dumps(comp, indent=2)
        except Exception:
            self.last_sim_result = str(comp)
        self.last_sim_final_percentage = comp.get('final_percentage', 0.0)
        self.last_sim_rating = comp.get('rating_label') or ''
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
