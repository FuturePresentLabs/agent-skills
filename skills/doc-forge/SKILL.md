---
name: doc-forge
description: 'Generate PDFs (and soon PNGs) from templates and letterheads via the doc-forge API. Use for: dealer packets, pricing sheets, shipping/packing slips, invoices, purchase orders, and Instagram carousel HTML. Supports Markdown+LaTeX and HTML+CSS workflows with Tera templating.'
metadata:
  {
    "openclaw": { "emoji": "📄", "requires": { "env": ["DOC_FORGE_API_KEY", "DOC_FORGE_BASE_URL"] } },
  }
---

# Doc Forge

Generate PDFs from templates and letterheads. Supports both Markdown+LaTeX and HTML+CSS rendering pipelines.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOC_FORGE_API_KEY` | API key for authentication | **Required** |
| `DOC_FORGE_BASE_URL` | Base URL for the API | `https://forge.gsgmfg.com` |

**Note:** Store credentials in `~/.config/doc-forge/credentials.json` or export inline:
```bash
export DOC_FORGE_API_KEY="your-api-key"
export DOC_FORGE_BASE_URL="https://forge.gsgmfg.com"
```

## API Overview

- **Base URL:** `DOC_FORGE_BASE_URL` (e.g., `https://forge.gsgmfg.com`)
- **Auth:** `X-API-Key: $DOC_FORGE_API_KEY`
- **Content-Type:** `application/json`

## Endpoints

### Health Check
```bash
curl "$DOC_FORGE_BASE_URL/health"
# Returns: "ok"
```

### Upload Letterhead
```bash
curl -X POST "$DOC_FORGE_BASE_URL/letterheads" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FPL_HTML",
    "tex": "<!DOCTYPE html><html>...</html>",
    "format": "html",
    "description": "Future Present Labs HTML letterhead"
  }'
```

**Formats:**
- `"format": "tex"` (default) — LaTeX letterhead for Pandoc/xelatex
- `"format": "html"` — HTML wrapper for WeasyPrint; use `{{ body | safe }}` to inject rendered template

### Upload Template
```bash
curl -X POST "$DOC_FORGE_BASE_URL/templates" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dealer_Packet",
    "schema": "Pricing",
    "letterhead": "FPL_HTML",
    "body": "<h1>Pricing for {{ dealer_name }}</h1>...",
    "format": "html",
    "stylesheet": "fixtures/css/gsg_invoice.css"
  }'
```

**Template Options:**
- `"format": "markdown"` (default) — Renders through Pandoc
- `"format": "html"` — Renders through WeasyPrint
- `"pdf_engine": "xelatex"` or `"weasyprint"` — Override default engine
- `"paper_size": "letter"` or `"a4"` or `"a6"` — Pandoc paper size
- `"stylesheet"` — Path or inline CSS for HTML templates

### Render PDF
```bash
curl -X POST "$DOC_FORGE_BASE_URL/render" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "Dealer_Packet",
    "data": {
      "dealer_name": "Acme Supply",
      "products": [...]
    }
  }'
# Returns: { "id": "uuid-here" }
```

### Fetch PDF
```bash
curl "$DOC_FORGE_BASE_URL/pdf/{id}" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  --output document.pdf
```

## Template Helpers

Available in all Tera templates:

| Helper | Usage | Output |
|--------|-------|--------|
| `md_table` | `{{ md_table(rows=items, columns=["SKU", "Price"], fields=["sku", "price"]) }}` | Markdown table |
| `money` | `{{ money(cents=123456, currency="$") }}` | `$1,234.56` |
| `wholesale_price` | `{{ wholesale_price(price_cents=10000, marked_price_cents=12000, discount_percent=15).display }}` | Discounted price object |
| `image_asset` | `{{ image_asset(url="https://...").uri }}` | Data URI for inline images |

## Examples

### Recall Existing Template

Check what templates exist by rendering with known names:

```bash
# Common GSG template names:
# - "GSG_HTML_Invoice" — Standard invoice
# - "Thermal_Packing_Slip" — A6 thermal packing slip
# - "GSG_Sku_Catalog" — SKU merchandising catalog
# - "GSG_Bulk_Quote" — Bulk quote form
# - "GSG_Purchase_Order" — Purchase order

# Render an existing template
curl -X POST "$DOC_FORGE_BASE_URL/render" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "GSG_HTML_Invoice",
    "data": {
      "company": { "name": "Grey Summit Gear" },
      "invoice": {
        "id": "INV-2048",
        "line_items": [
          { "sku": "GSG-04", "name": "Rounded Detent Pin", "qty": 5, "price": 12.50 }
        ]
      }
    }
  }'
```

### Create New Dealer Packet Template

```bash
# 1. Upload letterhead (if not exists)
curl -X POST "$DOC_FORGE_BASE_URL/letterheads" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "name": "Brand_Letterhead",
  "tex": "<!DOCTYPE html><html><head><style>body{font-family:sans-serif;margin:40px}</style></head><body>{{ body | safe }}</body></html>",
  "format": "html"
}
EOF

# 2. Upload template
curl -X POST "$DOC_FORGE_BASE_URL/templates" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "name": "Dealer_Pricing_Packet",
  "schema": "Pricing",
  "letterhead": "Brand_Letterhead",
  "format": "html",
  "body": "<h1>{{ brand_name }} Pricing</h1><table>{% for tier in pricing_tiers %}<tr><td>{{ tier.name }}</td><td>{{ tier.price }}</td></tr>{% endfor %}</table>"
}
EOF

# 3. Render
curl -X POST "$DOC_FORGE_BASE_URL/render" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "template": "Dealer_Pricing_Packet",
  "data": {
    "brand_name": "Acme Tools",
    "pricing_tiers": [
      { "name": "Dealer", "price": "$45.00" },
      { "name": "Distributor", "price": "$38.00" }
    ]
  }
}
EOF
```

### Generate Packing Slip

```bash
curl -X POST "$DOC_FORGE_BASE_URL/render" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "Thermal_Packing_Slip",
    "data": {
      "company": { "name": "Grey Summit Gear", "short_name": "GSG" },
      "order": {
        "id": "PO-10284",
        "ship_date": "2024-04-14",
        "shipping": {
          "name": "Jordan Safety",
          "address_line1": "845 Harbor Way",
          "city": "Seattle", "region": "WA", "postal_code": "98101"
        },
        "line_items": [
          { "sku": "GSG-04", "name": "Rounded Detent Pin", "qty": 5 }
        ]
      }
    }
  }'
```

### Batch Render (Multiple PDFs Concatenated)

```bash
curl -X POST "$DOC_FORGE_BASE_URL/render" \
  -H "X-API-Key: $DOC_FORGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "GSG_HTML_Invoice",
    "data": [
      { "invoice": { "id": "INV-001", ... } },
      { "invoice": { "id": "INV-002", ... } }
    ]
  }'
# Returns single PDF with both invoices concatenated
```

## Use Cases

| Use Case | Template Type | Notes |
|----------|---------------|-------|
| **Dealer packets** | HTML + CSS | Brand-specific pricing, tier tables |
| **Shipping/packing slips** | HTML + CSS, A6 size | Thermal printer friendly |
| **Invoices** | HTML + CSS or Markdown + LaTeX | Line items, totals, tax |
| **Purchase orders** | HTML + CSS | Signature blocks, terms |
| **SKU catalogs** | HTML + CSS | Category groupings, step-down pricing |
| **Instagram carousels** *(coming soon)* | HTML → PNG | Theme-based HTML generation for social |

## Multi-Tenant Metadata

All endpoints support optional scoping fields:

```json
{
  "realm_id": "global",
  "tenant_id": "warehouse",
  "user_id": "ops-bot",
  "data_classification": "internal"
}
```

**Classifications:** `public`, `internal` (default), `confidential`, `restricted`

## Caching

- Identical render requests (same template, metadata, and data) are cached for ~15 minutes
- Repeated POSTs within the window return the same document ID without re-rendering

## Coming Soon: PNG Support

PNG rendering is in development for social media workflows (Instagram carousels). The API will support:
- HTML template → PNG conversion
- Configurable dimensions (1080x1350 for Instagram)
- Theme-based generation from inputs

**Rev 2 Preview:**
```bash
# Future endpoint (not yet available)
POST /render
{
  "template": "Instagram_Carousel",
  "format": "png",
  "dimensions": { "width": 1080, "height": 1350 },
  "data": { "theme": "minimal", "slides": [...] }
}
```

## Error Handling

| Status | Meaning |
|--------|---------|
| `400` | Invalid request, missing template/letterhead, empty render data |
| `401` | Missing or incorrect API key |
| `404` | Template or letterhead not found |
| `500` | Rendering failure (Pandoc/WeasyPrint error) |

Error response:
```json
{
  "error": "failed to render document",
  "details": "pandoc invocation failed: ..."
}
```

## Local Development

```bash
# Clone and run locally
git clone https://github.com/FuturePresentLabs/doc-forge.git
cd doc-forge
cargo run

# Or with Docker
docker build -t doc-forge .
docker run --rm -p 3030:3030 -v "$(pwd)/storage:/data" doc-forge
```

Local defaults:
- Base URL: `http://localhost:3030`
- Data dir: `./storage`
- Pandoc path: `pandoc` on `$PATH`

## See Also

- Repository: `FuturePresentLabs/doc-forge`
- Fixtures: `fixtures/letterheads/`, `fixtures/templates/`, `fixtures/css/`
- Scripts: `scripts/run_real_pdf_tests.sh`, `scripts/render_remote_catalog.sh`