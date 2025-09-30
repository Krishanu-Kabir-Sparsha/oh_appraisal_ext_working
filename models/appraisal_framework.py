# -*- coding: utf-8 -*-
from odoo import api, fields, models

class OHAppraisalFramework(models.Model):
    _name = 'oh.appraisal.framework'
    _description = 'Assessment Framework (reviewer weight distribution)'

    name = fields.Char(required=True, help="Name this framework (e.g., '360-degree 50/30/20').")
    description = fields.Text(help="Explain typical usage and recommended reviewer types.")

    # Each framework contains weighted reviewer types (self, peer, manager, subordinate, customer).
    weight_line_ids = fields.One2many('oh.appraisal.framework.line','framework_id', string='Reviewer Weights',
                                     help="Define the weight (%) for each reviewer type. Percentages should sum to 100 for meaningful aggregation.")

    def compute_aggregate(self, scores_by_reviewer_type):
        """
        Aggregate a dict of reviewer_type -> numeric score (raw on same scale) into a single
        weighted raw value using configured weight_line_ids.
        If some configured reviewer type is missing from input, it contributes 0 (you may prefer different behavior).
        """
        self.ensure_one()
        total = 0.0
        for ln in self.weight_line_ids:
            typ = ln.reviewer_type
            wt = float(ln.weight or 0.0)
            val = float(scores_by_reviewer_type.get(typ, 0.0) or 0.0)
            total += (val * (wt / 100.0))
        return total


class OHAppraisalFrameworkLine(models.Model):
    _name = 'oh.appraisal.framework.line'
    _description = 'Framework Reviewer Weight Line'

    framework_id = fields.Many2one('oh.appraisal.framework', required=True, ondelete='cascade')
    reviewer_type = fields.Selection([
        ('self','Self'),
        ('peer','Peer'),
        ('manager','Manager'),
        ('subordinate','Subordinate'),
        ('customer','Customer')
    ], required=True, string="Reviewer Type")
    weight = fields.Float(string='Weight %', help='Percentage weight assigned to this reviewer type. Ensure total of lines = 100 for correct aggregation.')
