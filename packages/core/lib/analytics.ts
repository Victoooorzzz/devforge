// packages/core/lib/analytics.ts

type EventName =
  | "waitlist_signup"
  | "trial_started"
  | "checkout_started"
  | "checkout_completed"
  | "feature_used";

interface EventProps {
  feature_name?: string;
  [key: string]: string | number | boolean | undefined;
}

declare global {
  interface Window {
    plausible?: (
      eventName: string,
      options?: { props?: Record<string, string | number | boolean> }
    ) => void;
  }
}

export function trackEvent(eventName: EventName, props?: EventProps): void {
  if (typeof window === "undefined") return;

  const cleanProps: Record<string, string | number | boolean> = {};
  if (props) {
    for (const [key, value] of Object.entries(props)) {
      if (value !== undefined) {
        cleanProps[key] = value;
      }
    }
  }

  if (window.plausible) {
    window.plausible(eventName, {
      props: Object.keys(cleanProps).length > 0 ? cleanProps : undefined,
    });
  }

  if (process.env.NODE_ENV === "development") {
    console.log(`[Analytics] ${eventName}`, cleanProps);
  }
}

export function PlausibleScript({ domain }: { domain: string }): React.ReactElement {
  const React = require("react");
  return React.createElement("script", {
    defer: true,
    "data-domain": domain,
    src: "https://plausible.io/js/script.js",
  });
}
