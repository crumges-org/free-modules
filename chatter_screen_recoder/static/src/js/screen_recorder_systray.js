/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ScreenRecorderSystray extends Component {
    static components = { Dropdown };
    static props = [];
    static template = "chatter_screen_recoder.ScreenRecorderSystray";

    setup() {
        this.screenRecorder = useState(useService("screen_recorder"));
        this.dropdown = useDropdownState();
    }

    get isVisible() {
        return this.screenRecorder.isRecording || this.screenRecorder.isPaused || this.screenRecorder.isUploading;
    }

    onClickSave() {
        this.dropdown.close();
        this.screenRecorder.stopAndSave();
    }

    onClickPause() {
        this.screenRecorder.pauseRecording();
    }

    onClickResume() {
        this.screenRecorder.resumeRecording();
    }

    onClickDiscard() {
        this.dropdown.close();
        this.screenRecorder.discardRecording();
    }
}

registry
    .category("systray")
    .add("screen_recorder", { Component: ScreenRecorderSystray }, { sequence: 10 });
