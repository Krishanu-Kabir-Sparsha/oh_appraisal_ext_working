/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class AppraisalDashboard extends Component {
    setup() {
         this.orm = useService("orm");
        this.state = useState({
            industries: [],
            companies: [],
            departments: [],
            jobPositions: [],
            master: {
                industry: false,
                company: false,
                period: 'annual'
            },
            department: {
                selected: false,
                assessment_period: 'annual'
            },
            role: {
                selected: false
            },
            weightage: {
                functional: 35,
                role: 45,
                common: 20
            },
            framework: {
                primary: '360-degree',
                scale: '1-5'
            },
            simulation: {
                score: 85,
                rating: 'Exceeds'
            }
        });

        onWillStart(async () => {
            await this.loadConfiguration();
        });
    }

    async loadConfiguration() {
        // Load industries
        const industries = await this.orm.searchRead(
            'oh.appraisal.industry',
            [['active', '=', true]],
            ['id', 'name']
        );
        this.state.industries = industries;

        // Load companies
        const companies = await this.orm.searchRead(
            'res.company',
            [],
            ['id', 'name']
        );
        this.state.companies = companies;

        // Load departments
        const departments = await this.orm.searchRead(
            'hr.department',
            [],
            ['id', 'name']
        );
        this.state.departments = departments;

        // Load job positions
        const jobs = await this.orm.searchRead(
            'hr.job',
            [],
            ['id', 'name']
        );
        this.state.jobPositions = jobs;
    }

    async onWeightageChange(type, value) {
        this.state.weightage[type] = parseInt(value);
        // Validate total = 100%
        const total = Object.values(this.state.weightage).reduce((a, b) => a + b, 0);
        if (total !== 100) {
            // Adjust other values proportionally
            const remaining = 100 - this.state.weightage[type];
            const others = Object.entries(this.state.weightage).filter(([k]) => k !== type);
            const totalOthers = others.reduce((sum, [_, v]) => sum + v, 0);
            others.forEach(([k, v]) => {
                this.state.weightage[k] = Math.round((v / totalOthers) * remaining);
            });
        }
    }

    async runSimulation() {
        await this.orm.call(
            'oh.appraisal.master', 
            'action_run_simulation',
            [[this.state.master.id]]
        );
        this.state.simulation.score = 85;
        this.state.simulation.rating = 'Exceeds';
    }
}

AppraisalDashboard.template = "oh_appraisal_ext.Dashboard";
registry.category("actions").add("oh_appraisal_dashboard", AppraisalDashboard);