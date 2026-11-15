import { ArrowUpRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import LiquidGlass from "./LiquidGlass";

const StatsCard = ({ title, value, change, icon: Icon, gradient }: { title: string; value: string; change: number; icon: LucideIcon; gradient: string }) => {
  return (
    <LiquidGlass className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-navy-800/70">{title}</p>
          <h2 className="text-2xl font-bold text-navy-950">{value}</h2>
          <p className="flex items-center gap-1 text-sm text-emerald-400">
            <ArrowUpRight size={16} /> {change}%
          </p>
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${gradient}`}>
          <Icon size={22} className="text-white" />
        </div>
      </div>
    </LiquidGlass>
  );
};

export default StatsCard;
