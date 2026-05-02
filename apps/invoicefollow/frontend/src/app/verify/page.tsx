'use client';
import { VerifyEmail } from "@devforge/ui";
import { product } from "@/config/product";
import Link from "next/link";

export default function VerifyPage() {
  return (
    <div className="min-h-screen bg-black flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-8">
        <Link href="/" className="text-3xl font-bold tracking-tighter text-white">
          {product.name.split(' ')[0]}<span className="text-indigo-500">{product.name.split(' ')[1] || ''}</span>
        </Link>
      </div>
      <VerifyEmail />
    </div>
  );
}
