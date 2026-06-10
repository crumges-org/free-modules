/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEffect, useState } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.kxRecordingService = useService("kx_video_recording");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.action = useService("action");
        this.kxPlayback = useService("kx_recording_playback");
        this.kxRecordings = useState({ list: [], loading: false });

        useEffect(
            () => {
                this._kxLoadRecordings();
            },
            () => [this.state.thread?.model, this.state.thread?.id]
        );
    },

    get kxShowScreenRecording() {
        if (!this.kxRecordingService.isEnabled() || !this.kxRecordingService.isSupported()) {
            return false;
        }
        if (this.ui.isSmall) {
            return false;
        }
        const thread = this.state.thread;
        return Boolean(thread?.id && thread?.model);
    },

    get kxShowRecordingsList() {
        return (
            this.kxShowScreenRecording &&
            (this.kxRecordings.loading || this.kxRecordings.list.length > 0)
        );
    },

    async _kxLoadRecordings() {
        const thread = this.state.thread;
        if (!thread?.id || !this.kxRecordingService.isEnabled()) {
            this.kxRecordings.list = [];
            return;
        }
        this.kxRecordings.loading = true;
        try {
            this.kxRecordings.list = await this.orm.call(
                "kx.screen.recording",
                "search_read_for_document",
                [thread.model, thread.id]
            );
        } catch {
            this.kxRecordings.list = [];
        } finally {
            this.kxRecordings.loading = false;
        }
    },

    kxFormatDuration(seconds) {
        const s = Math.floor(seconds || 0);
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}:${String(r).padStart(2, "0")}`;
    },

    onClickPlayKxRecording(recordingId) {
        this.kxPlayback.playByRecordingId(recordingId);
    },

    onClickDownloadKxRecording(rec) {
        if (rec.attachment_id) {
            this.kxRecordingService.downloadRecordingAttachment(rec.attachment_id);
        }
    },

    async onClickEmailKxRecording(recordingId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Email recording"),
            res_model: "kx.screen.recording.email.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: { default_recording_id: recordingId },
        });
    },

    async onClickShareKxRecording(recordingId) {
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Share recording"),
                res_model: "kx.screen.recording.share.wizard",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: { default_recording_id: recordingId },
            },
            {
                onClose: async () => {
                    await this._kxLoadRecordings();
                    const thread = this.state.thread;
                    if (thread?.fetchData) {
                        await thread.fetchData(["messages"]);
                    }
                },
            }
        );
    },

    async onClickRecordScreen(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const thread = this.state.thread;
        if (!thread?.id) {
            const saved = await this.props.saveRecord?.();
            if (!saved) {
                this.notification.add(_t("Save the record before recording."), { type: "warning" });
                return;
            }
        }
        const activeThread = this.state.thread;
        this.kxRecordingService.beginSession({
            resModel: activeThread.model,
            resId: activeThread.id,
            onSaved: async () => {
                await activeThread.fetchData(["attachments"]);
                await this._kxLoadRecordings();
                if (this.props.hasParentReloadOnAttachmentsChanged) {
                    this.reloadParentView();
                }
            },
        });
        this.kxRecordingService.requestOpenPanel();
    },
});
