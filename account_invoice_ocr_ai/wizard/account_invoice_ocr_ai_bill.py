import re

from odoo import Command, _, api, fields, models


class AccountInvoiceOcrAiBill(models.TransientModel):
    _name = "account.invoice.ocr.ai.bill"
    _description = "Vendor Bill Extracted by AI"

    wizard_id = fields.Many2one("account.invoice.ocr.ai.wizard", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="wizard_id.company_id")
    attachment_id = fields.Many2one("ir.attachment", string="File", readonly=True)
    error = fields.Char(readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", domain="[('company_id', 'in', (False, company_id))]")
    ai_partner_name = fields.Char(string="Vendor on File", readonly=True)
    ai_partner_vat = fields.Char(string="Tax ID on File", readonly=True)
    ref = fields.Char(string="Bill Reference")
    invoice_date = fields.Date(string="Bill Date")
    invoice_date_due = fields.Date(string="Due Date")
    currency_id = fields.Many2one("res.currency", string="Currency")
    prices_include_taxes = fields.Boolean(
        help="Unit prices printed on the document already include taxes. They are converted when needed.",
    )
    ai_amount_total = fields.Monetary(string="Total on File", currency_field="currency_id", readonly=True)
    amount_total = fields.Monetary(
        string="Estimated Total", currency_field="currency_id", compute="_compute_amount_total"
    )
    has_total_mismatch = fields.Boolean(compute="_compute_amount_total")
    line_ids = fields.One2many("account.invoice.ocr.ai.bill.line", "bill_id", string="Lines")
    move_id = fields.Many2one("account.move", string="Bill", readonly=True)

    @api.depends("line_ids.price_subtotal", "line_ids.tax_ids", "ai_amount_total", "prices_include_taxes")
    def _compute_amount_total(self):
        for bill in self:
            total = 0.0
            for line in bill.line_ids:
                rate = sum(line.tax_ids.filtered(lambda tax: tax.amount_type == "percent").mapped("amount"))
                total += line.price_subtotal if bill.prices_include_taxes else line.price_subtotal * (1 + rate / 100)
            bill.amount_total = total
            currency = bill.currency_id or bill.company_id.currency_id
            bill.has_total_mismatch = bool(
                bill.ai_amount_total and currency.compare_amounts(total, bill.ai_amount_total)
            )

    @api.depends("attachment_id", "ai_partner_name")
    def _compute_display_name(self):
        for bill in self:
            bill.display_name = bill.attachment_id.name or bill.ai_partner_name or _("Bill")

    @api.model
    def _get_vals_from_ai(self, data, company):
        """Turn the AI answer into the values of a bill and its lines."""
        partner = self._find_partner(data.get("vendor_name"), data.get("vendor_vat"), company)
        currency = self._find_currency(data.get("currency"))
        Line = self.env["account.invoice.ocr.ai.bill.line"]
        return {
            "partner_id": partner.id,
            "ai_partner_name": data.get("vendor_name"),
            "ai_partner_vat": data.get("vendor_vat"),
            "ref": data.get("bill_reference"),
            "invoice_date": data.get("bill_date") or False,
            "invoice_date_due": data.get("due_date") or False,
            "currency_id": (currency or company.currency_id).id,
            "prices_include_taxes": data.get("prices_include_taxes"),
            "ai_amount_total": data.get("amount_total") or 0.0,
            "line_ids": [
                Command.create(Line._get_vals_from_ai(line, partner, company)) for line in data.get("lines") or []
            ],
        }

    @api.model
    def _find_partner(self, name, vat, company):
        domain = [("company_id", "in", (False, company.id))]
        partner = self.env["res.partner"]
        if vat:
            partner = partner.search([*domain, ("vat", "=ilike", vat)], limit=1)
            digits = re.sub(r"\D", "", vat)
            if not partner and len(digits) >= 8:
                partner = partner.search([*domain, ("vat", "=ilike", digits)], limit=1)
        if not partner and name:
            partner = partner.search([*domain, ("name", "=ilike", name)], limit=1) or partner.search(
                [*domain, ("name", "ilike", name)], limit=1
            )
        return partner

    @api.model
    def _find_currency(self, code):
        if not code:
            return self.env["res.currency"]
        return self.env["res.currency"].with_context(active_test=False).search([("name", "=ilike", code)], limit=1)

    def _get_move_vals(self):
        self.ensure_one()
        vals = {
            "move_type": "in_invoice",
            "company_id": self.company_id.id,
            "journal_id": self.wizard_id.journal_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": (self.currency_id or self.company_id.currency_id).id,
            "invoice_line_ids": [Command.create(line._get_move_line_vals()) for line in self.line_ids],
        }
        if self.ref:
            vals["ref"] = self.ref
        if self.invoice_date:
            vals["invoice_date"] = self.invoice_date
        if self.invoice_date_due:
            vals["invoice_date_due"] = self.invoice_date_due
        return vals

    def _create_move(self):
        self.ensure_one()
        move = self.env["account.move"].with_company(self.company_id).create(self._get_move_vals())
        self.move_id = move
        if self.attachment_id:
            # the file belongs to the wizard, move it to the bill before posting it in its chatter
            self.attachment_id.write({"res_model": move._name, "res_id": move.id})
            move.message_post(
                body=_("Draft created by AI from %s.", self.attachment_id.name),
                attachment_ids=self.attachment_id.ids,
            )
        return move
