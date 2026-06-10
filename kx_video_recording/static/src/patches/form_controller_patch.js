/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount, useEffect } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.kxRecording = useService("kx_video_recording");
        useEffect(
            () => {
                this._kxSyncRecordingFormLink();
            },
            () => [
                this.model.root.resId,
                this.model.root.resModel,
                this.model.root.data?.display_name,
                this.model.root.isNew,
            ]
        );
        onWillUnmount(() => {
            this.kxRecording?.clearFormLink?.();
        });
    },

    _kxSyncRecordingFormLink() {
        if (!this.kxRecording?.isEnabled?.()) {
            return;
        }
        const root = this.model.root;
        if (
            root.resId &&
            root.resModel &&
            !root.isNew &&
            root.resModel !== "kx.screen.recording"
        ) {
            const data = root.data || {};
            this.kxRecording.setFormLink({
                resModel: root.resModel,
                resId: root.resId,
                displayName:
                    data.display_name ||
                    data.name ||
                    `${root.resModel} #${root.resId}`,
            });
        } else {
            this.kxRecording.clearFormLink();
        }
    },
});
