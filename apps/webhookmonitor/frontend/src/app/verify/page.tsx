'use client';
import { VerifyEmail } from "@devforge/ui";
import { product } from "@/config/product";
import Link from "next/link";
import Image from "next/image";
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
      <div className="mb-8 text-center sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="inline-flex items-center justify-center gap-3 text-white">
          <Image src="/devforge-logo-white.svg" alt="DevForge" width={132} height={30} className="h-7 w-auto" style={{ width: "auto", height: "auto" }} priority />
          <span className="border-l border-white/15 pl-3 text-sm font-semibold">DevForge</span>
        </Link>
      </div>
      <VerifyEmail onVerified={handleVerified} />
    </div>
  );
}
