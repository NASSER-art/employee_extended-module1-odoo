/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

/**
 * Permit Notification Widget
 * Displays alerts for expiring driving permits in the systray
 */
class PermitNotification extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            permitAlerts: [],
            count: 0,
        });

        onWillStart(async () => {
            await this.loadPermitAlerts();
        });
    }

    async loadPermitAlerts() {
        const result = await this.orm.call(
            "hr.employee",
            "get_permit_alerts_count",
            []
        );
        this.state.count = result || 0;
    }

    async onClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Alertes Permis de Conduire",
            res_model: "hr.permit.alert",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["warning", "critical", "expired"]]],
            target: "current",
        });
    }
}

PermitNotification.template = "employee_extended.PermitNotificationMenu";

export const systrayItem = {
    Component: PermitNotification,
};

registry.category("systray").add("PermitNotification", systrayItem, { sequence: 50 });
