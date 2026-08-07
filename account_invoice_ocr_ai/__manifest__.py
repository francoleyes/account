{
    "name": "Vendor Bills OCR with Odoo AI",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Upload pictures or PDFs of vendor bills and let Odoo AI create the drafts",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "account",
        "ai",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_invoice_ocr_ai_wizard_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
