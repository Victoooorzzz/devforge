# PriceTrackr sample URLs

These URLs are from Books to Scrape, a public sandbox made for scraping tests.

| Product name | URL | Current visible price |
|---|---|---:|
| A Light in the Attic | https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html | 51.77 |
| Tipping the Velvet | https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html | 53.74 |
| Soumission | https://books.toscrape.com/catalogue/soumission_998/index.html | 50.10 |

Good test flow:

1. Add each URL with frequency `Cada 24h`.
2. Open a product row and confirm price/current stock/history.
3. Set an alert threshold below the current price, for example `45.00`.
4. Test export as CSV/XLSX/JSON.
