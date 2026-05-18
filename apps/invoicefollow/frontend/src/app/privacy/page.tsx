import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Privacy Policy</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Last updated: May 2024</p>
          <p>En InvoiceFollow, valoramos su privacidad. Esta política explica cómo recopilamos, usamos y protegemos sus datos.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">1. Collected Data</h2>
          <p>Recopilamos su dirección de correo electrónico para la gestión de cuentas y comunicación, y datos de uso de la aplicación para mejorar nuestros servicios.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">2. Procesamiento de Pagos</h2>
          <p>Sus pagos son procesados de forma segura por Lemon Squeezy. Nosotros no almacenamos información de su tarjeta de crédito.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">3. Contacto</h2>
          <p>Para solicitudes de eliminación de datos o dudas sobre privacidad, contáctenos en support@devforgeapp.pro.</p>
        </div>
      </div>
    </div>
  );
}
