/** @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.screenRecorder = useState(useService("screen_recorder"));
    },

    async onStartScreenRecording() {
        if (!this.props.threadId) {
            if (this.props.saveRecord) {
                await this.props.saveRecord();
            }
            if (!this.props.threadId) {
                this.env.services.notification.add(
                    _t("Please save the record before recording."),
                    { type: "warning" }
                );
                return;
            }
        }

        const model = this.props.threadModel;
        const id = this.props.threadId;
        const name = this.state.thread?.displayName || `${model} #${id}`;

        await this.screenRecorder.startRecording(model, id, name);
     },
});
