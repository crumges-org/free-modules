/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';


publicWidget.registry.websiteCourseExtended = publicWidget.Widget.extend({
    selector: '.o_course_extended',

    /**
     * @override
     */
    start: function () {
        $('.o_course_extended').on('click','#collapse_div',function() {
            var id = this.dataset.target.split('-')[1]
            if($('#slide-'+id).is(":visible")) {
                $('#slide-'+id).hide()
                $(this).children().first().children().removeClass('fa-minus');
                $(this).children().first().children().addClass('fa-plus');
            }else {
                $('#slide-'+id).show()
                $(this).children().first().children().removeClass('fa-plus');
                $(this).children().first().children().addClass('fa-minus');
            }
        });
    }
})
