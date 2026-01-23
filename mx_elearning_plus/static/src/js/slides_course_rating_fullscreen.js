/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";
import { sprintf } from '@web/core/utils/strings';
import { _t } from "@web/core/l10n/translation";
import '@website_slides/js/slides';

var FullscreenSlideLikeWidget = publicWidget.Widget.extend({
    events: {
        'click .o_wslides_js_slide_like_up_mx': '_onClickUpMx',
        'click .o_wslides_js_slide_like_down_mx': '_onClickDownMx',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            delay: {'hide': 300},
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickMx: function (slideId, voteType) {
        var self = this;
        rpc('/slides/slide/like', {
            slide_id: slideId,
            upvote: voteType === 'like',
        }).then(function (data) {
            if (! data.error) {
                const $likesBtn = self.$('span.o_wslides_js_slide_like_up_mx');
                const $likesIcon = $likesBtn.find('i.fa');
                const $dislikesBtn = self.$('span.o_wslides_js_slide_like_down_mx');
                const $dislikesIcon = $dislikesBtn.find('i.fa');

                // update 'thumbs-up' button with latest state
                $likesBtn.data('user-vote', data.user_vote);
                $likesBtn.find('span').text(data.likes);
                $likesIcon.toggleClass("fa-thumbs-up", data.user_vote === 1);
                $likesIcon.toggleClass("fa-thumbs-o-up", data.user_vote !== 1);
                // update 'thumbs-down' button with latest state
                $dislikesBtn.data('user-vote', data.user_vote);
                $dislikesBtn.find('span').text(data.dislikes);
                $dislikesIcon.toggleClass("fa-thumbs-down", data.user_vote === -1);
                $dislikesIcon.toggleClass("fa-thumbs-o-down", data.user_vote !== -1);
            } else {
                if (data.error === 'public_user') {
                    const message = data.error_signup_allowed ?
                        _t('Please <a href="/web/login?redirect=%s">login</a> or <a href="/web/signup?redirect=%s">create an account</a> to vote for this lesson') :
                        _t('Please <a href="/web/login?redirect=%s">login</a> to vote for this lesson');
                    self._popoverAlert(self.$el, sprintf(message, document.URL, document.URL));
                } else if (data.error === 'slide_access') {
                    self._popoverAlert(self.$el, _t('You don\'t have access to this lesson'));
                } else if (data.error === 'channel_membership_required') {
                    self._popoverAlert(self.$el, _t('You must be member of this course to vote'));
                } else if (data.error === 'channel_comment_disabled') {
                    self._popoverAlert(self.$el, _t('Votes and comments are disabled for this course'));
                } else if (data.error === 'channel_karma_required') {
                    self._popoverAlert(self.$el, _t('You don\'t have enough karma to vote'));
                } else {
                    self._popoverAlert(self.$el, _t('Unknown error'));
                }
            }
        });
    },

    _onClickUpMx: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
        return this._onClickMx(slideId, 'like');
    },

    _onClickDownMx: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
        return this._onClickMx(slideId, 'dislike');
    },
});

publicWidget.registry.FullscreenWebsiteSlidesSlideLike = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        $('.o_wslides_js_slide_like_mx').each(function () {
            defs.push(new FullscreenSlideLikeWidget(self).attachTo($(this)));
        });
        return Promise.all(defs);
    },
});

export default {
    FullscreenSlideLikeWidget: FullscreenSlideLikeWidget,
    FullscreenWebsiteSlidesSlideLike: publicWidget.registry.FullscreenWebsiteSlidesSlideLike
};
