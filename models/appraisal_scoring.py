# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OHAppraisalScoring(models.Model):
    _name = 'oh.appraisal.scoring'
    _description = 'Scoring Scale / Framework'
    _order = 'scale_min asc'

    name = fields.Char(string="Name", required=True, help="Descriptive name for this scoring scale (e.g., '1-5 scale').")
    description = fields.Text(string="Notes", help="Optional description/explanation for administrators.")

    scale_min = fields.Float(string="Minimum Scale", required=True,
                             help="Lowest numeric value of the scoring scale (no default — configure for your industry).")
    scale_max = fields.Float(string="Maximum Scale", required=True,
                             help="Highest numeric value of the scoring scale (no default — configure for your industry).")

    company_id = fields.Many2one('res.company', string="Company",
                                 help="Company for which this scoring scale applies. Leave blank to make it global.")

    rating_line_ids = fields.One2many(
        'oh.appraisal.scoring.line',
        'scoring_id',
        string='Rating Lines',
        copy=True,
        help="Define ranges on the scoring scale and corresponding human-readable labels (e.g. 4.5-5 => 'Outstanding')."
    )

    @api.constrains('scale_min', 'scale_max')
    def _check_scale(self):
        for rec in self:
            if rec.scale_max <= rec.scale_min:
                raise ValidationError(_("Maximum scale must be greater than minimum scale."))

    def normalize_to_percent(self, value):
        """Normalize a raw value on this scale to percent (0..100)."""
        self.ensure_one()
        try:
            v = float(value or 0.0)
        except Exception:
            v = 0.0
        denom = (self.scale_max - self.scale_min)
        if denom <= 0:
            return 0.0
        v = max(self.scale_min, min(v, self.scale_max))
        return ((v - self.scale_min) / denom) * 100.0

    def to_label(self, raw_value):
        """
        Map a raw numeric value (on this scoring scale) to a rating label by
        searching rating_line_ids. Returns None if no match.
        """
        self.ensure_one()
        if not self.rating_line_ids:
            return False
        try:
            rv = float(raw_value)
        except Exception:
            return False
        for ln in self.rating_line_ids.sorted(key=lambda r: r.min_value):
            if ln.min_value <= rv <= ln.max_value:
                return ln.label
        return False

    def evaluate_value(self, raw_value):
        """Return dict {'percent':..., 'label':...} for the given raw value."""
        self.ensure_one()
        return {
            'percent': self.normalize_to_percent(raw_value),
            'label': self.to_label(raw_value),
        }


class OHAppraisalScoringLine(models.Model):
    _name = 'oh.appraisal.scoring.line'
    _description = 'Scoring Label Line'
    _order = 'min_value asc'

    scoring_id = fields.Many2one('oh.appraisal.scoring', string="Scoring Framework", required=True, ondelete='cascade')
    min_value = fields.Float(string="Min value", required=True, help="Lower bound (inclusive) on the scoring scale.")
    max_value = fields.Float(string="Max value", required=True, help="Upper bound (inclusive) on the scoring scale.")
    label = fields.Char(string="Label", required=True, help="Label returned when raw value falls into the defined range.")

    @api.constrains('min_value', 'max_value')
    def _check_value_range(self):
        for rec in self:
            if rec.max_value <= rec.min_value:
                raise ValidationError(_("Maximum value must be greater than minimum value for each rating line."))
