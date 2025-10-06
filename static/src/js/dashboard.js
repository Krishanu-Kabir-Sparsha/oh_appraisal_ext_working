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
            currentUserId: null,
            currentCompanyId: null,
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
        try {
            // Call a custom backend method to get current user's allowed companies
            const result = await this.orm.call(
                'res.users',
                'get_dashboard_config',
                []
            );

            console.log("Dashboard config from backend:", result);

            if (result) {
                const allowedCompanyIds = result.company_ids || [];
                const currentCompanyId = result.current_company_id || false;

                console.log("Allowed Company IDs:", allowedCompanyIds);
                console.log("Current Company ID:", currentCompanyId);

                this.state.currentUserId = result.user_id;
                this.state.currentCompanyId = currentCompanyId;

                // Load companies filtered by allowed companies
                if (allowedCompanyIds.length > 0) {
                    const companies = await this.orm.searchRead(
                        'res.company',
                        [['id', 'in', allowedCompanyIds]],
                        ['id', 'name'],
                        { order: 'name' }
                    );
                    this.state.companies = companies;
                    
                    console.log("Loaded Companies:", companies);

                    // Set default company
                    if (currentCompanyId) {
                        this.state.master.company = currentCompanyId;
                        await this.onCompanyChange(currentCompanyId);
                    }
                } else {
                    console.warn("No allowed companies found, loading all companies");
                    const companies = await this.orm.searchRead(
                        'res.company',
                        [],
                        ['id', 'name'],
                        { order: 'name' }
                    );
                    this.state.companies = companies;
                }
            }

            // Load industries
            const industries = await this.orm.searchRead(
                'oh.appraisal.industry',
                [['active', '=', true]],
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.industries = industries;
            
            console.log("Loaded Industries:", industries);

        } catch (error) {
            console.error("Error loading configuration:", error);
            console.error("Error details:", error.message);
            
            // Fallback: load all companies if user detection fails
            console.log("Falling back to load all companies");
            const companies = await this.orm.searchRead(
                'res.company',
                [],
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.companies = companies;
            console.log("Loaded all companies (fallback):", companies);

            // Load industries even if user detection fails
            const industries = await this.orm.searchRead(
                'oh.appraisal.industry',
                [['active', '=', true]],
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.industries = industries;
        }

        // Load departments and job positions (initially load all)
        await this.loadDepartmentsAndJobs();
    }

    async loadDepartmentsAndJobs(companyId = false) {
        try {
            const domain = companyId ? [['company_id', '=', companyId]] : [];
            
            // Load departments
            const departments = await this.orm.searchRead(
                'hr.department',
                domain,
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.departments = departments;
            console.log("Loaded Departments:", departments);

            // Load job positions
            const jobs = await this.orm.searchRead(
                'hr.job',
                domain,
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.jobPositions = jobs;
            console.log("Loaded Job Positions:", jobs);
        } catch (error) {
            console.error("Error loading departments/jobs:", error);
        }
    }

    async onCompanyChange(ev) {
        // Handle both event object and direct value
        const companyId = ev?.target ? parseInt(ev.target.value) : parseInt(ev);
        
        console.log("Company change triggered with:", companyId);
        
        if (!companyId) {
            this.state.departments = [];
            this.state.jobPositions = [];
            this.state.department.selected = false;
            this.state.role.selected = false;
            return;
        }

        // Update the state
        this.state.master.company = companyId;

        // Load departments and jobs for selected company
        await this.loadDepartmentsAndJobs(companyId);

        // Reset dependent selections
        this.state.department.selected = false;
        this.state.role.selected = false;
    }

    async onWeightageChange(type, value) {
        this.state.weightage[type] = parseInt(value);
        const total = Object.values(this.state.weightage).reduce((a, b) => a + b, 0);
        
        if (total !== 100) {
            const remaining = 100 - this.state.weightage[type];
            const others = Object.entries(this.state.weightage).filter(([k]) => k !== type);
            const totalOthers = others.reduce((sum, [_, v]) => sum + v, 0);
            
            if (totalOthers > 0) {
                others.forEach(([k, v]) => {
                    this.state.weightage[k] = Math.round((v / totalOthers) * remaining);
                });
            }
        }
    }

    async runSimulation() {
        try {
            if (this.state.master.id) {
                await this.orm.call(
                    'oh.appraisal.master',
                    'action_run_simulation',
                    [[this.state.master.id]]
                );
            }
            // Update simulation results
            this.state.simulation.score = 85;
            this.state.simulation.rating = 'Exceeds';
            
            console.log("Simulation completed");
        } catch (error) {
            console.error("Error running simulation:", error);
        }
    }

    openIndustryTypes() {
        // Open Industry Types configuration in a new action
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Industry Types',
            res_model: 'oh.appraisal.industry',
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list,form',
            target: 'current',
        });
    }
}

AppraisalDashboard.template = "oh_appraisal_ext.Dashboard";
registry.category("actions").add("oh_appraisal_dashboard", AppraisalDashboard);