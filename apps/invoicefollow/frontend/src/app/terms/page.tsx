import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Terms of Service</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Last updated: May 2024</p>
          <p>Al utilizar InvoiceFollow, usted acepta estos términos. Proveemos esta herramienta "tal cual", sin garantías de ningún tipo. Usted es responsable del uso que le dé a la plataforma.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">1. Use of Service</h2>
          <p>You must not use our service for any illegal or unauthorized purpose. El abuso de la plataforma resultará en la terminación de su cuenta.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">2. Payments y Suscripciones</h2>
          <p>Ofrecemos un trial gratuito de 7 días. Luego se realizará un cobro de $9.99/mes. Puede cancelar en cualquier momento antes de que se procese el cargo.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">3. Cambios en los Términos</h2>
          <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Le notificaremos de cambios significativos.</p>
        </div>
      </div>
    </div>
  );
}
