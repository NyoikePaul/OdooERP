/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

class EstateDashboard extends Component {
    static template = "kenya_real_estate.Dashboard";

    setup() {
        this.orm  = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            const data = await this.orm.call(
                "estate.dashboard", "get_dashboard_data", []);
            this.state.data    = data;
            this.state.loading = false;
        } catch (e) {
            console.error("Dashboard error:", e);
            this.state.loading = false;
        }
    }

    async refresh() {
        this.state.loading = true;
        await this.loadData();
    }

    openAction(xmlid) {
        this.action.doAction(xmlid);
    }

    fmt(n) {
        if (!n) return "0";
        return new Intl.NumberFormat("en-KE").format(Math.round(n));
    }
}

registry.category("actions").add("estate_dashboard", EstateDashboard);
export default EstateDashboard;
