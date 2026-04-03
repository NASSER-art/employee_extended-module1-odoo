/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

/**
 * Composant de notification pour les alertes de permis de conduire.
 * Affiche un badge dans le systray avec le nombre de permis expirants.
 */
class PermitAlertSystray extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            alertCount: 0,
            alerts: [],
            isLoaded: false,
        });

        onWillStart(async () => {
            await this.loadAlerts();
        });

        // Rafraîchir toutes les 10 minutes
        this.refreshInterval = setInterval(() => {
            this.loadAlerts();
        }, 600000);
    }

    async loadAlerts() {
        try {
            const count = await this.orm.call(
                "hr.employee",
                "get_permit_alerts_count",
                []
            );
            this.state.alertCount = count;

            if (count > 0) {
                const alerts = await this.orm.call(
                    "hr.employee",
                    "get_permit_alerts_data",
                    []
                );
                this.state.alerts = alerts;

                // ✅ Vérifier si notification déjà affichée aujourd'hui
                const today = new Date().toISOString().split('T')[0];
                const lastNotificationDate = localStorage.getItem('permit_alert_last_date');
                const shouldShowNotification = lastNotificationDate !== today;

                // Notification si des permis sont expirés
                const expiredCount = alerts.filter(
                    (a) => a.status === "expired"
                ).length;
                if (expiredCount > 0 && shouldShowNotification) {
                    this.notification.add(
                        `⚠️ ${expiredCount} permis de conduire expiré(s) ! Veuillez vérifier.`,
                        {
                            type: "danger",
                            sticky: true,
                            title: "Alerte Permis",
                        }
                    );
                    // ✅ Marquer comme affiché aujourd'hui
                    localStorage.setItem('permit_alert_last_date', today);
                }

                const criticalCount = alerts.filter(
                    (a) => a.status === "critical"
                ).length;
                if (criticalCount > 0 && shouldShowNotification) {
                    this.notification.add(
                        `${criticalCount} permis expire(nt) dans moins de 15 jours.`,
                        {
                            type: "warning",
                            sticky: false,
                            title: "Permis - Expiration proche",
                        }
                    );
                    // ✅ Marquer comme affiché aujourd'hui
                    localStorage.setItem('permit_alert_last_date', today);
                }
            }

            this.state.isLoaded = true;
        } catch (error) {
            console.warn("Impossible de charger les alertes de permis:", error);
        }
    }

    /**
     * Ouvrir la vue des alertes de permis au clic sur le badge
     */
    async onClickAlerts() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Alertes Permis de Conduire",
            res_model: "hr.permit.alert",
            view_mode: "tree,kanban,form",
            views: [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ],
            target: "current",
            context: {
                search_default_filter_expired: 1,
                search_default_filter_critical: 1,
                search_default_filter_warning: 1,
            },
        });
    }

    /**
     * Déterminer la classe CSS du badge selon la gravité
     */
    getBadgeClass() {
        if (this.state.alertCount === 0) return "d-none";
        const hasExpired = this.state.alerts.some((a) => a.status === "expired");
        const hasCritical = this.state.alerts.some(
            (a) => a.status === "critical"
        );
        if (hasExpired) return "badge bg-danger rounded-pill";
        if (hasCritical) return "badge bg-warning rounded-pill";
        return "badge bg-info rounded-pill";
    }
}

PermitAlertSystray.template = "employee_extended.PermitAlertSystray";
PermitAlertSystray.props = {};

// Template XML inline via OWL
PermitAlertSystray.template = owl.xml`
    <div class="o_permit_alert_systray" t-on-click="onClickAlerts"
         style="cursor: pointer;" title="Alertes permis de conduire">
        <t t-if="state.alertCount > 0">
            <i class="fa fa-car fa-lg" style="margin-right: 4px;"/>
            <span t-att-class="getBadgeClass()">
                <t t-esc="state.alertCount"/>
            </span>
        </t>
    </div>
`;

// Enregistrer dans le systray
registry
    .category("systray")
    .add("employee_extended.PermitAlertSystray", {
        Component: PermitAlertSystray,
    }, { sequence: 90 });

export default PermitAlertSystray;