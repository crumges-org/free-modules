/** @odoo-module **/

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useBus, useService } from "@web/core/utils/hooks";

export class KxRecordingSystray extends Component {
    static template = "kx_video_recording.RecordingSystray";
    static components = { Dropdown };
    static props = {};

    setup() {
        this.recording = useService("kx_video_recording");
        this.action = useService("action");
        this.recState = this.recording.state;
        this.uiTick = useState({ n: 0 });
        this.dropdown = useDropdownState();
        this.liveVideoRef = useRef("liveVideo");
        this.playbackVideoRef = useRef("playbackVideo");

        useBus(this.recording.bus, "KX_RECORDING_OPEN_PANEL", () => {
            this.dropdown.open();
        });

        useBus(this.recording.bus, "KX_RECORDING_PREVIEW_SYNC", () => {
            this.uiTick.n++;
            this._syncVideoElements();
        });

        useBus(this.recording.bus, "KX_RECORDING_PREPARE_START", () => {
            this.recording.clearVideoElement(this.liveVideoRef.el);
            this.recording.clearVideoElement(this.playbackVideoRef.el);
        });

        // Duration updates in a service interval; bump uiTick so the systray badge re-renders.
        useBus(this.recording.bus, "KX_RECORDING_TICK", () => {
            this.uiTick.n++;
        });

        useEffect(
            () => {
                this._syncVideoElements();
            },
            () => [this.recState.phase, this.recState.previewRevision]
        );
    }

    formatDuration(seconds) {
        const s = Math.floor(seconds || 0);
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}:${String(r).padStart(2, "0")}`;
    }

    _syncVideoElements() {
        const live = this.liveVideoRef.el;
        const playback = this.playbackVideoRef.el;
        if (this.recState.phase === "preview") {
            this.recording.clearVideoElement(live);
            this.recording.attachPlaybackPreview(playback);
        } else if (this.recState.phase === "ready") {
            this.recording.clearVideoElement(playback);
            this.recording.attachLivePreview(live);
        } else if (this.recState.phase === "recording") {
            this.recording.clearVideoElement(playback);
            this.recording.clearVideoElement(live);
        } else {
            this.recording.clearVideoElement(live);
            this.recording.clearVideoElement(playback);
        }
    }

    get isRecording() {
        return this.recState.phase === "recording";
    }

    get supportsPause() {
        return this.recording.supportsPauseResume();
    }

    get showLivePreview() {
        return this.recState.phase === "ready" || this.recState.phase === "preview";
    }

    get showRecordingPlaceholder() {
        return this.recState.phase === "recording";
    }

    onBeforeOpen() {
        // Fresh start when reopening after a saved recording (or first open from idle).
        if (this.recState.phase === "idle" || this.recState.phase === "saved") {
            this.recording.beginSession({ openPanel: false });
        }
        queueMicrotask(() => this._syncVideoElements());
    }

    onRecordCurrentTab() {
        this.recording.pickScreen("current");
    }

    onPickOtherScreen() {
        this.recording.pickScreen("other");
    }

    onStartRecording() {
        this.recording.startRecording();
    }

    onPauseRecording() {
        this.recording.pauseRecording();
    }

    onResumeRecording() {
        this.recording.resumeRecording();
    }

    onStopRecording() {
        this.recording.stopRecording();
    }

    onChangeScreen() {
        this.recording.changeScreen();
    }

    onDiscardPreview() {
        this.recording.discardPreview();
    }

    onCancel() {
        this.recording.cancelSession();
        this.dropdown.close();
    }

    onRecordingNameInput(ev) {
        this.recording.setRecordingName(ev.target.value);
        this.uiTick.n++;
    }

    onSave() {
        this.recording.saveRecording();
    }

    onViewSaved() {
        this.recording.viewLastSaved();
    }

    onNewRecording() {
        this.recording.startAnotherRecording();
    }

    onDismissSaved() {
        this.recording.dismissSaved();
        this.dropdown.close();
    }

    onToggleAutoDelete(ev) {
        this.recState.autoDelete = ev.target.checked;
        this.uiTick.n++;
    }

    onAutoDeleteDaysChange(ev) {
        this.recState.autoDeleteDays = parseInt(ev.target.value, 10) || 30;
        this.uiTick.n++;
    }

    onToggleLinkDocument(ev) {
        this.recording.setLinkToCurrentDocument(ev.target.checked);
        this.uiTick.n++;
    }

    onToggleIncludeMic(ev) {
        this.recState.includeMic = ev.target.checked;
        this.uiTick.n++;
    }

    onToggleIncludeSystemAudio(ev) {
        this.recState.includeSystemAudio = ev.target.checked;
        this.uiTick.n++;
    }

    onDownloadSaved() {
        this.recording.downloadLastSaved();
    }

    async onEmailSaved() {
        const id = this.recording.state.lastSaved?.id;
        if (!id) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Email recording",
            res_model: "kx.screen.recording.email.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: { default_recording_id: id },
        });
    }
}

export const kxRecordingSystrayItem = {
    Component: KxRecordingSystray,
    isDisplayed(env) {
        if (env.isSmall) {
            return false;
        }
        const svc = env.services["kx_video_recording"];
        return Boolean(svc?.isEnabled?.() && svc?.isSupported?.());
    },
};

registry.category("systray").add("kx_video_recording.systray", kxRecordingSystrayItem, {
    sequence: 45,
});
