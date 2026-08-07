# Vendor Bills OCR with Odoo AI

Upload pictures or PDFs of vendor bills and let the AI read them and create the drafts.

## Usage

*Accounting > Vendors > Digitize Bills with AI*

1. Pick the purchase journal and upload one or more files. **Each file is read as a separate
   bill**: a picture per bill, or a multi page PDF per bill.
2. *Extract with AI*: every file is sent to the AI, one request per file.
3. Review what was read (vendor, reference, dates, currency, lines, taxes). A warning shows up
   when the total of the lines does not match the total printed on the document.
4. *Create Drafts*: one draft vendor bill per file, with the file attached in its chatter.

A file that could not be read (not a bill, unsupported format, AI error) is reported on its own
row and does not stop the others.

## Configuration

The AI provider and its API key come from the `ai` module (*Settings > General Settings > AI*).
The model used to read the bills is set in *Settings > Accounting > Digitization > Digitize Bills
with AI*, and defaults to `gpt-4.1`.

## What is matched automatically

- **Vendor**: by tax id, then by name. Left empty when there is no match, and required to create
  the draft.
- **Taxes**: purchase tax of the company with the same rate as the one read on the line.
- **Products**: only by code (internal reference, barcode or vendor code). Matching on the
  description is too unreliable to be done automatically, so lines without a code are created as
  a description only, and the accounts are the ones Odoo computes by default.

## Notes

- Pictures are converted to PDF before being sent: the AI service downscales images too much to
  read a bill, while PDF pages are sent as they are.
- `prices_include_taxes` is read from the document; unit prices are converted when the convention
  of the matched tax is the other one.
