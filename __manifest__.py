# -*- coding: utf-8 -*-
{
    "name": "OH Appraisal - Extended Templates & Weightage Engine (PRO)",
    "version": "18.0.2.1.0",
    "category": "Human Resources",
    "summary": "Advanced appraisal: templates, weightage engine, scoring, results, OKR & KPI integration",
    "author": "Your Company",
    "depends": [
        "base",
        "web",
        "oh_appraisal",
        "hr",
        "survey",
        "hr_holidays"
    ],
    "data": [
        "security/oh_appraisal_ext_groups.xml",
        "security/ir.model.access.csv",
        "data/cron_reminders.xml",
        "views/views_industry.xml",
        "views/views_master.xml", 
        "views/views_templates.xml",
        "views/views_scoring.xml",
        "views/views_results.xml",
        "views/views_primary_framework.xml",
        "views/dashboard.xml",
        "views/hr_appraisal_ext_views.xml",
        "views/menuitems.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Fix paths to match directory structure
            "oh_appraisal_ext/static/src/js/dashboard.js",
            "oh_appraisal_ext/static/src/css/dashboard.css",
            "oh_appraisal_ext/static/src/xml/dashboard_template.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "AGPL-3",
}