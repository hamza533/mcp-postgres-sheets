import { CircleCheckIcon, InfoIcon, type LucideIcon, ShieldAlertIcon, TriangleAlertIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type Variant = "info" | "warning" | "security" | "success";

const styles: Record<Variant, { box: string; icon: string; Icon: LucideIcon }> = {
  info: { box: "bg-info-soft border-info/25 border-l-info", icon: "text-info", Icon: InfoIcon },
  warning: {
    box: "bg-warn-soft border-warn/25 border-l-amber-500",
    icon: "text-amber-500",
    Icon: TriangleAlertIcon,
  },
  security: {
    box: "bg-danger-soft border-danger/25 border-l-danger",
    icon: "text-danger",
    Icon: ShieldAlertIcon,
  },
  success: {
    box: "bg-brand-soft border-brand/25 border-l-brand",
    icon: "text-brand",
    Icon: CircleCheckIcon,
  },
};

/** Callout banner (DESIGN.md "Alerts & Callout Banners"): tinted, 1px border, 3.5px left rule. */
export function Callout({
  variant = "info",
  title,
  children,
  className,
  ...props
}: {
  variant?: Variant;
  title?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
} & React.ComponentProps<"div">) {
  const { box, icon, Icon } = styles[variant];
  return (
    <div
      role="note"
      className={cn("not-prose my-5 flex gap-3 rounded-lg border border-l-[3.5px] p-4", box, className)}
      {...props}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", icon)} />
      <div className="min-w-0 text-sm">
        {title ? <p className="text-foreground font-semibold">{title}</p> : null}
        {children ? <div className="text-foreground/75 mt-1 [&_p]:my-0">{children}</div> : null}
      </div>
    </div>
  );
}

/** Solid success banner ("You're connected"). */
export function SuccessBanner({
  title,
  children,
  ...props
}: { title: React.ReactNode; children?: React.ReactNode } & React.ComponentProps<"div">) {
  return (
    <div
      role="status"
      className="not-prose bg-primary text-primary-foreground my-6 flex gap-3 rounded-lg p-5"
      {...props}
    >
      <CircleCheckIcon className="mt-0.5 size-5 shrink-0" />
      <div className="text-sm">
        <p className="text-[15px] font-semibold">{title}</p>
        {children ? <div className="mt-1 opacity-90">{children}</div> : null}
      </div>
    </div>
  );
}
