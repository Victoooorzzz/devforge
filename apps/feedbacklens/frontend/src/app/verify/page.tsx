'use client';
import { VerifyEmail } from "@devforge/ui";
import { product } from "@/config/product";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@devforge/core";

export default function VerifyPage() {
  const router = useRouter();

  const handleVerified = async () => {
    try {
      const { data } = await apiClient.post("/polar/checkout", {
        app_name: product.name
      }) as { data: { checkout_url: string } };
      window.location.href = data.checkout_url;
    } catch (err) {
      router.push("/dashboard");
    }
  };

  return (
    <div className="min-h-screen bg-black flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-8">
        <Link href="/" className="text-3xl font-bold tracking-tighter text-white">
          {product.name.split(' ')[0]}<span className="text-orange-500">{product.name.split(' ')[1] || ''}</span>
        </Link>
      </div>
      <VerifyEmail onVerified={handleVerified} />
    </div>
  );
}
