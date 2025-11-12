/** @odoo-module **/

import { ListRenderer } from '@web/views/list/list_renderer';
import { patch } from '@web/core/utils/patch';

patch(ListRenderer.prototype, {
    async _renderHeaderCell(column) {
        const result = await super._renderHeaderCell(...arguments);
        
        // Define which fields should show help icons
        const fieldsWithHelp = {
            'key_objective_breakdown': 'Select the objective breakdown parameter for this key result',
            'breakdown_priority': 'Priority level: High (red), Medium (yellow), Low (blue)',
            'team_id': 'Select the team responsible for this key result',
            'metric': 'Type of measurement:\n• Percentage: For percentage-based metrics\n• Count: For numeric quantities\n• Rating: For scale-based ratings\n• Score: For points-based scoring',
            'actual_value': 'Actual numeric value achieved/measured',
            'target_value': 'Target numeric value to be achieved',
            'achieve': 'Achievement status or assessment (To be configured)',
            'distributed_weightage': 'Weightage allocated to this objective breakdown'
        };

        // Check if this column has help text
        if (column.name in fieldsWithHelp) {
            // Add help icon to the header
            const headerCell = result;
            const helpIcon = document.createElement('span');
            helpIcon.innerHTML = ' <span class="o_help_icon" title="' + fieldsWithHelp[column.name] + '">?</span>';
            headerCell.appendChild(helpIcon);
        }

        return result;
    }
});