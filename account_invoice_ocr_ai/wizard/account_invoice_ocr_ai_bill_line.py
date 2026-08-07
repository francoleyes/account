from odoo import Command, api, fields, models


class AccountInvoiceOcrAiBillLine(models.TransientModel):
    _name = "account.invoice.ocr.ai.bill.line"
    _description = "Vendor Bill Line Extracted by AI"

    bill_id = fields.Many2one("account.invoice.ocr.ai.bill", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="bill_id.company_id")
    currency_id = fields.Many2one(related="bill_id.currency_id")
    name = fields.Char(string="Description", required=True)
    ai_product_code = fields.Char(string="Code on File", readonly=True)
    product_id = fields.Many2one(
        "product.product", string="Product", domain="[('company_id', 'in', (False, company_id))]"
    )
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float(string="Unit Price", digits="Product Price")
    discount = fields.Float(string="Discount (%)")
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
    )
    price_subtotal = fields.Monetary(string="Subtotal", currency_field="currency_id", compute="_compute_price_subtotal")

    @api.depends("quantity", "price_unit", "discount")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit * (1 - line.discount / 100)

    @api.model
    def _get_vals_from_ai(self, data, partner, company):
        product = self._find_product(data.get("product_code"), partner, company)
        return {
            "name": data.get("description") or (product.display_name if product else "/"),
            "ai_product_code": data.get("product_code"),
            "product_id": product.id,
            "quantity": data.get("quantity") or 0.0,
            "price_unit": data.get("price_unit") or 0.0,
            "discount": data.get("discount") or 0.0,
            "tax_ids": [Command.set(self._find_taxes(data.get("tax_rate"), company).ids)],
        }

    @api.model
    def _find_product(self, code, partner, company):
        """Match on codes only: matching on the description is too unreliable to be automatic."""
        Product = self.env["product.product"]
        if not code:
            return Product
        domain = [("company_id", "in", (False, company.id))]
        product = Product.search([*domain, ("default_code", "=ilike", code)], limit=1) or Product.search(
            [*domain, ("barcode", "=", code)], limit=1
        )
        if not product and partner:
            supplierinfo = self.env["product.supplierinfo"].search(
                [("partner_id", "=", partner.id), ("product_code", "=ilike", code)], limit=1
            )
            product = supplierinfo.product_id or supplierinfo.product_tmpl_id.product_variant_id
        return product

    @api.model
    def _find_taxes(self, rate, company):
        if rate is None:
            return self.env["account.tax"]
        return self.env["account.tax"].search(
            [
                ("type_tax_use", "=", "purchase"),
                ("amount_type", "=", "percent"),
                ("amount", "=", rate),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )

    def _get_price_unit(self):
        """Unit price in the convention of the company, from the price printed on the document."""
        self.ensure_one()
        rate = sum(self.tax_ids.filtered(lambda tax: tax.amount_type == "percent").mapped("amount"))
        if not rate:
            return self.price_unit
        tax_included = any(self.tax_ids.mapped("price_include"))
        if self.bill_id.prices_include_taxes and not tax_included:
            return self.price_unit / (1 + rate / 100)
        if not self.bill_id.prices_include_taxes and tax_included:
            return self.price_unit * (1 + rate / 100)
        return self.price_unit

    def _get_move_line_vals(self):
        self.ensure_one()
        vals = {
            "name": self.name,
            "quantity": self.quantity,
            "price_unit": self._get_price_unit(),
            "discount": self.discount,
            "tax_ids": [Command.set(self.tax_ids.ids)],
        }
        if self.product_id:
            vals["product_id"] = self.product_id.id
        return vals
