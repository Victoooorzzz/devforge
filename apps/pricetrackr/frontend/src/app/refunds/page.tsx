import Link from "next/link";

export default function RefundsPage() {
  return (
    <div className="min-h-screen bg-black text-white p-10 md:p-24 selection:bg-accent selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-accent hover:underline mb-8 inline-block">&larr; Volver al inicio</Link>
        <h1 className="text-4xl font-bold mb-6">Refund Policy</h1>
        <div className="space-y-4 text-neutral-300">
          <p>Last updated: May 2024</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Período de Prueba y Cargos</h2>
          <p>Para asegurar la satisfacción de nuestros usuarios, PriceTrackr ofrece un <strong>período de prueba gratuito de 7 días</strong>. Durante este tiempo, usted tiene acceso completo a las funciones de infraestructura de grado empresarial de nuestra plataforma, permitiéndole evaluar si cumple con sus necesidades.</p>
          <p>Una vez transcurridos los 7 días de prueba, se procesará automáticamente el cargo mensual recurrente de <strong>$9.99 dólares</strong>.</p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Refund Policy Definitivos</h2>
          <p>Debido a que ofrecemos este período de prueba extendido para que usted evalúe libremente el producto, <strong>una vez procesado el cargo de la suscripción, todas las ventas son definitivas y no se emiten reembolsos bajo ninguna circunstancia.</strong></p>
          <h2 className="text-2xl font-semibold mt-6 mb-2">Cancelaciones</h2>
          <p>Usted es libre de cancelar su suscripción en cualquier momento antes de que se cumpla el período de prueba para evitar cobros, o en cualquier momento posterior para evitar futuros cobros mensuales. Puede realizar la cancelación directamente desde su panel de control o a través de los correos de Lemon Squeezy.</p>
        </div>
      </div>
    </div>
  );
}
