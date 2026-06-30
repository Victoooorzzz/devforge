import { getProduct } from "@devforge/core";
import { ProductLandingPage } from "@devforge/ui";

export default function HomePage() {
  return <ProductLandingPage product={getProduct("webhookmonitor")} />;
}
