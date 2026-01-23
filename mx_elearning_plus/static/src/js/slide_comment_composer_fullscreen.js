/** @odoo-module **/
    
import publicWidget from '@web/legacy/js/public/public_widget';
import portalComposer from "@portal/js/portal_composer";
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";

const PortalComposer = portalComposer.PortalComposer;


PortalComposer.include({
    /**
     * @private
     * @param {Event} ev
     */
    async _onSubmitButtonClick(ev) {
        await this._super(...arguments).then((result) => {
            const $modal = this.$el.closest('#commentpopupcomposer');
            $modal.on('hidden.bs.modal', () => {
                this.trigger_up('reload_comment_popup_composer', result);
            });
            $modal.modal('hide');
        });
    },

    /**
     * Prepare message data for submission.
     *
     * @private
     * @returns {Object} The data object to be sent to the backend.
     */
    _prepareMessageData() {
        const messageBody = this.$('textarea[name="message"]').val();
        const attachmentIds = this.attachments.map((a) => a.id);
        const attachmentTokens = this.attachments.map((a) => a.access_token);

        if (this.options.is_comment_fullscreen) {
            const resId = $('.o_wslides_fs_sidebar_list_item.active').data('id');
            return {
                thread_model: this.options.res_model,
                thread_id: resId,
                post_data: {
                    body: messageBody,
                    attachment_ids: attachmentIds,
                    message_type: "comment",
                    subtype_xmlid: "mail.mt_comment",
                },
                attachment_tokens: attachmentTokens,
            };
        } else {
            return {
                thread_model: this.options.res_model,
                thread_id: this.options.res_id,
                post_data: {
                    body: messageBody,
                    attachment_ids: attachmentIds,
                    message_type: "comment",
                    subtype_xmlid: "mail.mt_comment",
                },
                attachment_tokens: attachmentTokens,
                message_id: this.options.default_message_id,
            };
        }
    },

});
/**
 * CommentPopupComposer
 *
 * Open a popup with the portal composer when clicking on it.
 **/
const CommentPopupComposer = publicWidget.Widget.extend({
    selector: '.o_comment_popup_composer',
    custom_events: {
        reload_comment_popup_composer: '_onReloadCommentPopupComposer',
    },

    willStart: function (parent) {
        const def = this._super.apply(this, arguments);
        const options = this.$el.data();
        this.options = Object.assign({
            'token': false,
            'res_model': false,
            'res_id': false,
            'pid': 0,
            'csrf_token': odoo.csrf_token,
            'user_id': session.user_id,
        }, options, {});
        return def;
    },

    /**
     * @override
     */
    start: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._reloadCommentPopupComposer(),
        ]);
    },

    /**
     * Destroy existing commentPopup and insert new commentPopup widget
     *
     * @private
     * @param {Object} data
     */
    _reloadCommentPopupComposer: function () {
        // Append the modal
        const modal = renderToElement(
            'mx_elearning_plus.PopupCommentComposer', {
            inline_mode: true,
            widget: this,
        });
        this.$('.o_comment_popup_composer_modal').html(modal);

        if (this._composer) {
            this._composer.destroy();
        }

        // Instantiate the "Portal Composer" widget and insert it into the modal
        this._composer = new PortalComposer(this, this.options);
        return this._composer.appendTo(this.$('.o_comment_popup_composer_modal .o_portal_chatter_composer'))
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onReloadCommentPopupComposer: function (event) {
        const data = event.data;
        this.options = Object.assign(this.options, data);

        this._reloadCommentPopupComposer();
    }
});

publicWidget.registry.CommentPopupComposer = CommentPopupComposer;

export default CommentPopupComposer;
