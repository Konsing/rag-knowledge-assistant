import { useEffect, useRef } from "react";

declare global {
  interface Window {
    hcaptcha?: {
      render: (container: HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

interface Props {
  siteKey: string;
  resetNonce: number;
  onVerify: (token: string) => void;
}

const SCRIPT_ID = "hcaptcha-script";

export default function HCaptcha({ siteKey, resetNonce, onVerify }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    function renderWidget() {
      if (cancelled || widgetRef.current || !containerRef.current || !window.hcaptcha) return;
      widgetRef.current = window.hcaptcha.render(containerRef.current, {
        sitekey: siteKey,
        theme: "dark",
        callback: (token: string) => onVerify(token),
        "expired-callback": () => onVerify(""),
        "error-callback": () => onVerify(""),
      });
    }

    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      if (window.hcaptcha) renderWidget();
      else existing.addEventListener("load", renderWidget, { once: true });
    } else {
      const script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.src = "https://js.hcaptcha.com/1/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      script.addEventListener("load", renderWidget, { once: true });
      document.head.appendChild(script);
    }

    return () => {
      cancelled = true;
      if (widgetRef.current && window.hcaptcha) {
        window.hcaptcha.remove(widgetRef.current);
        widgetRef.current = null;
      }
    };
  }, [siteKey, onVerify]);

  useEffect(() => {
    if (widgetRef.current && window.hcaptcha) {
      window.hcaptcha.reset(widgetRef.current);
      onVerify("");
    }
  }, [resetNonce, onVerify]);

  return <div ref={containerRef} className="min-h-[78px]" aria-label="Bot verification" />;
}
