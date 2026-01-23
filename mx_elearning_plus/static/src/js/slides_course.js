/** @odoo-module **/

import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

Fullscreen.include({
    events: Object.assign({}, Fullscreen.prototype.events, {
        'click .o_btn_comment_unable': '_onClickCommentUnable',
        'click .o_btn_comment_public': '_onClickCommentPublic',
        'click .o_btn_no_comment_karma': '_onClickNoCommentKarma',
        'click .o_btn_comment_karma': '_onClickCommentKarma',
    }),

    _onClickCommentUnable: function () {
        var message = ('Commenting is not enabled on this course.');
        this.displayNotification({
            type: 'warning',
            message: message,
            sticky: true
        });
    },

    _onClickCommentPublic: function () {
        var message = ('There are no comments for now. Join Course to be the first to leave a comment.');
        this.displayNotification({
            type: 'warning',
            message: message,
            sticky: true
        });
    },

    _onClickNoCommentKarma: function () {
        var message = ('There are no comments for now. Earn more Karma to be the first to leave a comment.');
        this.displayNotification({
            type: 'warning',
            message: message,
            sticky: true
        });
    },

    _onClickCommentKarma: function () {
        var message = ('Earn more Karma to leave a comment.');
        this.displayNotification({
            type: 'warning',
            message: message,
            sticky: true
        });
    },
    
    _renderSlide: function () {
        this._super.apply(this, arguments);
        const slide = this._slideValue;
        rpc('/slides/slide/mx/like', {
            slide_id: slide.id,
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
                $('.o_wslides_js_slide_like_up_mx').data('slide-id', slide.id);
                $('.o_wslides_js_slide_like_down_mx').data('slide-id', slide.id);
                $('.o_wslides_js_slide_like_up_mx span').text(data.likes);
                $('.o_wslides_js_slide_like_down_mx span').text(data.dislikes);
            }
        });
    },

    _onChangeSlideRequest: function (ev){
        this._super.apply(this, arguments);
        var slideData = ev.data;
        var $data = this.$el.prevObject.find('.js_publish_btn:visible').parents(".js_publish_management:first");
        rpc('/website/publish/slide', {
            id: slideData.id,
        }).then(function (result) {
            if (result){
                $data.removeClass("css_unpublished");
                $data.addClass("css_published");
                $data.find('input').prop("checked", result);
                $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
            }else{
                $data.removeClass("css_published");
                $data.addClass("css_unpublished");
                $data.find('input').prop("checked", result);
                $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
            }
        })
    }
});
