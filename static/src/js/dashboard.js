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
                functional: '',
                role: '',
                common: ''
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

    // Update the saveConfiguration method:
    async saveConfiguration() {
        try {
            if (!this.state.department.selected) {
                alert('Please select a department first');
                return;
            }

            if (!this.state.master.company) {
                alert('Please select a company first');
                return;
            }

            // Validate weightages
            const functional = parseFloat(this.state.weightage.functional) || 0;
            const role = parseFloat(this.state.weightage.role) || 0;
            const common = parseFloat(this.state.weightage.common) || 0;
            const total = functional + role + common;

            if (total !== 100) {
                alert('Total weightage must equal 100%');
                return;
            }

            // Save complete configuration
            const result = await this.orm.call(
                'oh.appraisal.department.weightage',
                'save_department_config',
                [
                    this.state.department.selected,
                    this.state.master.company,
                    {
                        functional_weightage: functional,
                        role_weightage: role,
                        common_weightage: common,
                        assessment_period: this.state.department.assessment_period,
                        industry_type: this.state.master.industry
                    }
                ]
            );

            if (result) {
                // Refresh the configuration after saving
                await this.loadDepartmentConfig(
                    this.state.department.selected,
                    this.state.master.company
                );
                alert('Configuration saved successfully!');
            } else {
                throw new Error('Failed to save configuration');
            }
        } catch (error) {
            console.error("Error saving configuration:", error);
            alert('Error saving configuration: ' + (error.message || 'Unknown error'));
        }
    }

    // Add method to load existing configuration
    async loadDepartmentConfig(departmentId, companyId) {
        if (!departmentId || !companyId) return;

        try {
            const config = await this.orm.call(
                'oh.appraisal.department.weightage',
                'get_department_config',
                [],
                {
                    department_id: departmentId,
                    company_id: companyId
                }
            );

            if (config) {
                this.state.weightage.functional = config.functional_weightage;
                this.state.weightage.role = config.role_weightage;
                this.state.weightage.common = config.common_weightage;
                this.state.department.assessment_period = config.assessment_period;
            } else {
                // Clear weightages if no config exists
                this.state.weightage.functional = '';
                this.state.weightage.role = '';
                this.state.weightage.common = '';
            }
        } catch (error) {
            console.error("Error loading department config:", error);
        }
    }

    async loadDepartmentsAndJobs(companyId = false) {
        try {
            let departmentDomain = [];
            let jobDomain = [];
            
            if (companyId) {
                departmentDomain = [['company_id', '=', companyId]];
                jobDomain = [['company_id', '=', companyId]];
            }
            
            // Load departments
            const departments = await this.orm.searchRead(
                'hr.department',
                departmentDomain,
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.departments = departments;
            
            // Load job positions
            const jobs = await this.orm.searchRead(
                'hr.job',
                jobDomain,
                ['id', 'name'],
                { order: 'name' }
            );
            this.state.jobPositions = jobs;

        } catch (error) {
            console.error("Error loading departments/jobs:", error);
            this.state.departments = [];
            this.state.jobPositions = [];
        }
    }


    // Also update the onCompanyChange method to include loadDepartmentConfig:
    async onCompanyChange(ev) {
        const companyId = ev?.target ? parseInt(ev.target.value) : parseInt(ev);
        
        if (!companyId) {
            this.state.departments = [];
            this.state.jobPositions = [];
            this.state.department.selected = false;
            this.state.role.selected = false;
            this.state.weightage.functional = '';
            this.state.weightage.role = '';
            this.state.weightage.common = '';
            return;
        }

        this.state.master.company = companyId;
        
        // Load departments and jobs
        await this.loadDepartmentsAndJobs(companyId);
        
        // Reset selections
        this.state.department.selected = false;
        this.state.role.selected = false;
    }

    // Add a new method to handle department changes
    async onDepartmentChange(ev) {
        const departmentId = ev?.target ? parseInt(ev.target.value) : parseInt(ev);
        this.state.department.selected = departmentId;
        
        if (departmentId && this.state.master.company) {
            await this.loadDepartmentConfig(departmentId, this.state.master.company);
        } else {
            this.state.weightage.functional = '';
            this.state.weightage.role = '';
            this.state.weightage.common = '';
        }
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