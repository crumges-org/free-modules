/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { _t } from "@web/core/l10n/translation";
import { AudioSelectorDialog } from './audio_dialog';

// For Backend Part
export class AudioPlugin extends Plugin {
    static id = 'audio_plugin';
    static dependencies = ["selection", "history", "dom", "dialog"];
    resources = {
        user_commands: [
            {
                id: "openAudioDialog",
                title: _t("Audio Recorder"),
                description: _t("Insert an audio"),
                icon: "fa-file-audio-o",
                run: this.openAudioDialog.bind(this),
            },
        ],
        powerbox_items: [
            { categoryId: "media", commandId: "openAudioDialog" }
        ]
    }

    get recordInfo() {
        return this.config.getRecordInfo ? this.config.getRecordInfo() : {};
    }
    
    openAudioDialog(params = {}) {
        const selection = this.dependencies.selection.getEditableSelection();
        const restoreSelection = () => {
            this.dependencies.selection.setSelection(selection);
        };
        const { resModel, resId, field, type } = this.recordInfo;
        this.services.dialog.add(AudioSelectorDialog, {
            resModel,
            resId,
            useMediaLibrary: !!(
                field &&
                ((resModel === "ir.ui.view" && field === "arch") || type === "html")
            ),
            save: (element) => {
                this.onSaveMediaDialog(element, { restoreSelection });
            },
            onAttachmentChange: this.config.onAttachmentChange || (() => {}),
            noVideos: !!this.config.disableVideo,
            noImages: !!this.config.disableImage,
            extraTabs: this.getResource("media_dialog_extra_tabs"),
            ...this.config.mediaModalParams,
            ...params,
        });
    }

    onSaveMediaDialog(element, { restoreSelection }) {
        restoreSelection();
        this.dependencies.dom.insert(element);
        this.dependencies.history.addStep();
    }
}

MAIN_PLUGINS.push(AudioPlugin)