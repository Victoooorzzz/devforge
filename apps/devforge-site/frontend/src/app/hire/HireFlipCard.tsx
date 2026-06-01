"use client";

import { useState } from "react";

const experience = [
  "Creator of DevForge, a 5-product micro-SaaS monorepo",
  "Custom websites built with Next.js, React, and Tailwind CSS",
  "Landing pages, product pages, dashboards, and full web apps",
  "FastAPI backends, authentication, payments, and production deploys",
];

export function HireFlipCard() {
  const [isFlipped, setIsFlipped] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <button
      type="button"
      aria-pressed={isFlipped}
      onClick={() => setIsFlipped((value) => !value)}
      className="group block w-full cursor-pointer text-left [perspective:1400px] focus:outline-none"
    >
      <span className="sr-only">
        Flip profile card to {isFlipped ? "show summary" : "show photo and experience"}
      </span>
      <span
        className={[
          "relative block min-h-[760px] w-full transition-transform duration-700 [transform-style:preserve-3d]",
          isFlipped ? "[transform:rotateY(180deg)]" : "",
        ].join(" ")}
      >
        <span
          className="absolute inset-0 flex min-h-[760px] flex-col justify-between overflow-hidden rounded-[4px] border p-7 [backface-visibility:hidden] md:p-9"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "rgba(130,19,70,0.32)",
          }}
        >
          <span
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-20 blur-3xl"
            style={{ backgroundColor: "var(--color-accent)" }}
          />
          <span className="relative block">
            <span className="badge mb-8 rounded-[2px]">Available for custom builds</span>
            <span className="heading-section block text-3xl leading-tight md:text-5xl">
              Custom websites with the DevForge build standard.
            </span>
            <span
              className="mt-6 block max-w-xl text-base leading-relaxed md:text-lg"
              style={{ color: "var(--color-text-secondary)" }}
            >
              I design and build fast, clean, conversion-focused websites for founders,
              freelancers, and small businesses that need a serious web presence.
            </span>
          </span>

          <span className="relative grid gap-4 md:grid-cols-3">
            {["Strategy", "Design", "Build"].map((item) => (
              <span
                key={item}
                className="rounded-[4px] px-4 py-3 text-sm"
                style={{ backgroundColor: "var(--color-surface-raised)" }}
              >
                <span className="font-mono text-xs" style={{ color: "var(--color-accent)" }}>
                  {item}
                </span>
              </span>
            ))}
          </span>

          <span
            className="relative mt-8 block border-t pt-5 text-xs uppercase tracking-[0.18em]"
            style={{
              borderColor: "rgba(40,38,39,0.85)",
              color: "var(--color-text-secondary)",
              fontFamily: "'Chakra Petch', sans-serif",
            }}
          >
            Click to see the builder behind DevForge
          </span>
        </span>

        <span
          className="absolute inset-0 flex min-h-[760px] flex-col overflow-hidden rounded-[4px] border [backface-visibility:hidden] [transform:rotateY(180deg)]"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "rgba(130,19,70,0.32)",
          }}
        >
          <span className="relative flex h-[300px] shrink-0 items-center justify-center overflow-hidden bg-black p-4">
            {!imageFailed ? (
              <img
                src="/hire-profile.jpg"
                alt="DevForge developer portrait"
                className="h-full w-full object-contain grayscale"
                onError={() => setImageFailed(true)}
              />
            ) : (
              <span className="flex h-full min-h-[280px] items-center justify-center bg-[radial-gradient(circle_at_50%_20%,#383536_0%,#191718_38%,#050505_78%)] px-8 text-center">
                <span className="heading-section text-2xl">Profile Photo</span>
              </span>
            )}
            <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-70" />
          </span>

          <span className="flex flex-1 flex-col justify-between p-6 md:p-7">
            <span>
              <span className="font-mono text-xs" style={{ color: "var(--color-accent)" }}>
                EXPERIENCE
              </span>
              <span className="heading-section mt-3 block text-2xl leading-tight">
                I build the same way I build DevForge: lean, sharp, and production-ready.
              </span>
              <span className="mt-5 grid gap-2">
                {experience.map((item) => (
                  <span
                    key={item}
                    className="block rounded-[4px] px-3 py-2 text-xs leading-relaxed"
                    style={{
                      backgroundColor: "var(--color-surface-raised)",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    {item}
                  </span>
                ))}
              </span>
            </span>

            <span
              className="mt-4 block border-t pt-4 text-[11px] uppercase tracking-[0.16em]"
              style={{
                borderColor: "rgba(40,38,39,0.85)",
                color: "var(--color-text-secondary)",
                fontFamily: "'Chakra Petch', sans-serif",
              }}
            >
              Click again to flip back
            </span>
          </span>
        </span>
      </span>
    </button>
  );
}
