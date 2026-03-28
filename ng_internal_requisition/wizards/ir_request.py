from odoo import api, fields, models

class IrRequestWizard(models.TransientModel):
    _name = "ir.request.wizard"
    _description = "IR Request Rejection Wizard"

    reason = fields.Text(string="Reason", required=True)

    def reject(self):
        request_id = self.env.context.get("request_id")
        print(request_id)
        if request_id:
            request = self.env["ng.ir.request"].browse(request_id)
            request.write({
                "state": "draft",
                "reason": self.reason,
            })
        # return {"type": "ir.actions.act_window_close"}
