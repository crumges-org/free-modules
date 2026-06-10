// /** @odoo-module **/

// import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
// import { useService } from '@web/core/utils/hooks';
// import { patch } from "@web/core/utils/patch";


// patch(Wysiwyg.prototype, {

//     async _saveB64Image(el, resModel, resId) {
//         el.classList.remove('o_b64_image_to_save');
//         const imageData = el.getAttribute('src').split('base64,')[1];
//         if (!imageData) {
//             // Checks if the image is in base64 format for RPC call. Relying
//             // only on the presence of the class "o_b64_image_to_save" is not
//             // robust enough.
//             return;
//         }

//         // T2733 : In HTML fields, attachments will not create.
//         if (resModel == "shipment.stop") {
//             const closestDiv = el.closest('.o_field_widget.o_field_html');
//             const nameAttr = closestDiv?.getAttribute("name");
//             if (nameAttr === "directions" || nameAttr === "notes") {
//                 console.log("T2733..!!!!")
//                 return;
//             }
//         }

//         const attachment = await this._serviceRpc(
//             '/web_editor/attachment/add_data',
//             {
//                 name: el.dataset.fileName || '',
//                 data: imageData,
//                 is_image: true,
//                 res_model: resModel,
//                 res_id: resId,
//             },
//         );
//         if (attachment.mimetype === 'image/webp') {
//             el.classList.add('o_modified_image_to_save');
//             el.dataset.originalId = attachment.id;
//             el.dataset.mimetype = attachment.mimetype;
//             el.dataset.fileName = attachment.name;
//             this._saveModifiedImage(el, resModel, resId);
//         } else {
//             let src = attachment.image_src;
//             if (!attachment.public) {
//                 let accessToken = attachment.access_token;
//                 if (!accessToken) {
//                     [accessToken] = await this.orm.call(
//                         'ir.attachment',
//                         'generate_access_token',
//                         [attachment.id],
//                     );
//                 }
//                 src += `?access_token=${encodeURIComponent(accessToken)}`;
//             }
//             el.setAttribute('src', src);
//         }

//     }

// });
