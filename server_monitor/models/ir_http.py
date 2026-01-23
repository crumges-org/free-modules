import time

import werkzeug.exceptions

from odoo import models
from odoo.http import request

from ..odoo_metrics import REQUEST_METRICS


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _dispatch(cls, endpoint):
        start = time.perf_counter()
        status = 200
        exception_name = None
        try:
            response = super()._dispatch(endpoint)
            if hasattr(response, "status_code"):
                status = response.status_code
            return response
        except Exception as exc:
            exception_name = exc.__class__.__name__
            if isinstance(exc, werkzeug.exceptions.HTTPException) and exc.code:
                status = exc.code
            else:
                status = 500
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            try:
                path = request.httprequest.path if request and request.httprequest else "-"
                method = (
                    request.httprequest.method
                    if request and request.httprequest
                    else ""
                )
                REQUEST_METRICS.record(
                    path=path,
                    method=method,
                    status=status,
                    duration_ms=duration_ms,
                    exception=exception_name,
                )
            except Exception:
                # Avoid breaking requests if metrics collection fails.
                pass
