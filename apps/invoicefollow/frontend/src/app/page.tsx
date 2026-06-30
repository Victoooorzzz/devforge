import { getProduct } from "@devforge/core";
import { ProductLandingPage } from "@devforge/ui";

export default function HomePage() {
  const invoiceFollow = getProduct("invoicefollow");
  const landingProduct = {
    ...invoiceFollow,
    headline: "Track existing invoices, automate reminders, and reconcile payments.",
  };

  return <ProductLandingPage product={landingProduct} />;
}
