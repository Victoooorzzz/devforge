// packages/core/lib/analytics.ts

type EventName = string;

interface EventProps {
  feature_name?: string;
  [key: string]: string | number | boolean | undefined;
}

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
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

  if (window.gtag) {
    window.gtag("event", eventName, cleanProps);
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

export function GoogleAnalyticsScript({
  measurementId = "G-QHLMJM23RD",
}: {
  measurementId?: string;
}): React.ReactElement {
  const React = require("react");
  return React.createElement(
    React.Fragment,
    null,
    React.createElement("script", {
      async: true,
      src: `https://www.googletagmanager.com/gtag/js?id=${measurementId}`,
    }),
    React.createElement("script", {
      dangerouslySetInnerHTML: {
        __html: `window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${measurementId}');`,
      },
    })
  );
}
