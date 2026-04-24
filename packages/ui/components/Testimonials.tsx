// packages/ui/components/Testimonials.tsx
import React from "react";

interface Testimonial {
  quote: string;
  name: string;
  role: string;
  avatarInitial?: string;
}

interface TestimonialsProps {
  title?: string;
  testimonials: Testimonial[];
}

export function Testimonials({
  title = "Trusted by developers",
  testimonials,
}: TestimonialsProps) {
  return (
    <section className="py-20 md:py-28">
      <div className="section-container">
        <h2 className="heading-section text-3xl md:text-4xl text-center mb-16">
          {title}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="p-6 rounded-lg"
              style={{ backgroundColor: "var(--color-surface)" }}
            >
              <p
                className="text-sm leading-relaxed mb-6"
                style={{ color: "var(--color-text-secondary)" }}
              >
                &ldquo;{testimonial.quote}&rdquo;
              </p>
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold"
                  style={{
                    backgroundColor: "var(--color-accent-dim)",
                    color: "var(--color-accent)",
                  }}
                >
                  {testimonial.avatarInitial || testimonial.name.charAt(0)}
                </div>
                <div>
                  <p
                    className="text-sm font-medium"
                    style={{ color: "var(--color-text)" }}
                  >
                    {testimonial.name}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    {testimonial.role}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
