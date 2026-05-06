import type { ReactNode } from "react";

export type IconName =
  | "rocket"
  | "play"
  | "zap"
  | "package"
  | "workflow"
  | "check"
  | "document"
  | "code"
  | "test"
  | "refresh"
  | "shield";

export default function SvgIcon({ name, className }: { name: IconName; className?: string }) {
  const commonProps = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  const paths: Record<IconName, ReactNode> = {
    rocket: (
      <>
        <path d="M4.5 16.5c-1.2 1-1.8 2.5-1.5 4 1.5.3 3-.3 4-1.5" />
        <path d="M9 15 6 18" />
        <path d="M15 9l-6 6" />
        <path d="M14.5 4.5c2.1-.9 4.1-1 5.5-.5.5 1.4.4 3.4-.5 5.5-1 2.3-3 4.6-5.5 6.5L8 10c1.9-2.5 4.2-4.5 6.5-5.5Z" />
        <path d="M14 5v5h5" />
      </>
    ),
    play: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m10 8 6 4-6 4V8Z" />
      </>
    ),
    zap: <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />,
    package: (
      <>
        <path d="m21 8-9-5-9 5 9 5 9-5Z" />
        <path d="M3 8v8l9 5 9-5V8" />
        <path d="M12 13v8" />
        <path d="m7.5 5.5 9 5" />
      </>
    ),
    workflow: (
      <>
        <rect x="3" y="4" width="6" height="5" rx="1.5" />
        <rect x="15" y="4" width="6" height="5" rx="1.5" />
        <rect x="9" y="15" width="6" height="5" rx="1.5" />
        <path d="M9 6.5h6" />
        <path d="M6 9v2.5A3.5 3.5 0 0 0 9.5 15H12" />
        <path d="M18 9v2.5A3.5 3.5 0 0 1 14.5 15H12" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    document: (
      <>
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
        <path d="M14 3v5h5" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </>
    ),
    code: (
      <>
        <path d="m8 9-4 3 4 3" />
        <path d="m16 9 4 3-4 3" />
        <path d="m14 5-4 14" />
      </>
    ),
    test: (
      <>
        <path d="M9 11 12 14 22 4" />
        <path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11" />
      </>
    ),
    refresh: (
      <>
        <path d="M21 12a9 9 0 0 1-15.2 6.5" />
        <path d="M3 12A9 9 0 0 1 18.2 5.5" />
        <path d="M18 2v4h-4" />
        <path d="M6 22v-4h4" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9.5 12 1.8 1.8 3.7-4" />
      </>
    ),
  };

  return <svg {...commonProps}>{paths[name]}</svg>;
}
