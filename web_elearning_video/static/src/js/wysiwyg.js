/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import { preserveCursor } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { patch } from "@web/core/utils/patch";
import { VideoSelectorDialog } from './video_dialog';
import { AudioSelectorDialog } from './audio_dialog';

// For Frontend Part
patch(Wysiwyg.prototype, {
    /**
     * @override
     * @returns {Array[Object]}
     */
    _getPowerboxOptions() {
        const options = super._getPowerboxOptions();
        const { commands, categories } = options;
        categories.push({ name: _t('Media'), priority: 50 });
        commands.push({
            category: _t('Media'),
            name: _t('Video Recorder'),
            description: _t('Insert a Video'),
            fontawesome: 'fa-file-video-o',
            callback: (params = {}) => {
                const editable = this.$editable;
                const { resModel, resId, field, type } = this._getRecordInfo(editable);
                const restoreSelection = preserveCursor(this.odooEditor.document);
                this.env.services.dialog.add(params.VideoSelectorDialog || VideoSelectorDialog, {
                    resModel,
                    resId,
                    useMediaLibrary: !!(field && (resModel === 'ir.ui.view' && field === 'arch' || type === 'html')),
                    media: params.node,
                    save: this._onMediaDialogSave.bind(this, {
                        node: params.node,
                        restoreSelection: restoreSelection,
                    }),
                    onAttachmentChange: this._onAttachmentChange.bind(this),
                });
            },
        });
        commands.push({
            category: _t('Media'),
            name: _t('Audio Recorder'),
            description: _t('Insert an Audio'),
            fontawesome: 'fa-file-audio-o',
            callback: (params = {}) => {
                const editable = this.$editable;
                const { resModel, resId, field, type } = this._getRecordInfo(editable);
                const restoreSelection = preserveCursor(this.odooEditor.document);
                this.env.services.dialog.add(params.AudioSelectorDialog || AudioSelectorDialog, {
                    resModel,
                    resId,
                    useMediaLibrary: !!(field && (resModel === 'ir.ui.view' && field === 'arch' || type === 'html')),
                    media: params.node,
                    save: this._onMediaDialogSave.bind(this, {
                        node: params.node,
                        restoreSelection: restoreSelection,
                    }),
                    onAttachmentChange: this._onAttachmentChange.bind(this),
                });
            },
        });
        return { ...options, commands, categories };
    },
});