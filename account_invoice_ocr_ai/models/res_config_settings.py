from odoo import fields, models
from odoo.addons.ai.utils.llm_providers import PROVIDERS

from ..wizard.account_invoice_ocr_ai_wizard import DEFAULT_LLM_MODEL


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_invoice_ocr_ai_llm_model = fields.Selection(
        selection=lambda self: [
            (model, label)
            for provider in PROVIDERS
            for model, label in provider.llms
            if model not in provider.deprecated_models
        ],
        string="Bills Digitization Model",
        config_parameter="account_invoice_ocr_ai.llm_model",
        default=DEFAULT_LLM_MODEL,
    )
