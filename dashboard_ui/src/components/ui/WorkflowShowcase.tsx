import { useState } from "react";
import { motion } from "framer-motion";
import { DollarSign, ShoppingBag, Users } from "lucide-react";
import { useI18n } from "../../i18n";
import LiquidGlass from "./LiquidGlass";
import StatsCard from "./StatsCard";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const Statistics = () => {
  const [mode, setMode] = useState("weekly");
  const total = 30, done = 18;

  return (
    <LiquidGlass className="liquidGlass-paper p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-navy-950">Statistics</h3>
        <div className="flex rounded-full bg-ice p-1 text-xs">
          {["weekly", "monthly"].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-full px-3 py-1 capitalize ${mode === m ? "bg-navy-950 text-white" : "text-navy-800/70"}`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <p className="mt-4 text-4xl font-bold text-navy-950">
        {done}/{total} <span className="text-sm font-normal text-navy-800/70">tasks complete</span>
      </p>

      <div className="mt-3 flex gap-1">
        {Array.from({ length: total }).map((_, i) => (
          <div key={i} className={`h-3 flex-1 rounded-sm ${i < done ? "bg-navy-800" : "bg-steel-200"}`} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-ice p-4 text-center">
          <p className="text-2xl font-bold text-navy-950">12</p>
          <p className="text-xs text-navy-800/70">Project complete</p>
        </div>
        <div className="rounded-2xl bg-ice p-4 text-center">
          <p className="text-2xl font-bold text-navy-950">05</p>
          <p className="text-xs text-navy-800/70">Project in progress</p>
        </div>
      </div>
    </LiquidGlass>
  );
};

export function WorkflowShowcase() {
  const { t } = useI18n();
  return (
    <div className="space-y-4">
      <span className="badge">{t("source.sample")}</span>
      <LiquidGlass className="liquidGlass-members flex items-center justify-between bg-navy-950 p-8">
        <div>
          <h1 className="text-3xl text-white">
            Work's always <em className="text-orange-300">better</em> together
          </h1>
          <p className="mt-2 max-w-md text-sm text-white/60">
            Add teammates and you'll be able to collaborate and quickly get a sense of what's happening at work.
          </p>
        </div>
        <button type="button" className="rounded-full bg-orange-400 px-5 py-2 text-sm font-semibold text-navy-950 hover:bg-orange-300">
          Add member
        </button>
      </LiquidGlass>
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <motion.div variants={item}><Statistics /></motion.div>
        <motion.div variants={item} className="grid gap-4">
          <StatsCard title="Total Sales" value="$12.5K" change={12} icon={DollarSign} gradient="from-navy-800 to-navy-950" />
          <StatsCard title="Customers" value="1,284" change={8} icon={Users} gradient="from-steel-500 to-navy-800" />
          <StatsCard title="Orders" value="342" change={5} icon={ShoppingBag} gradient="from-orange-400 to-rose-500" />
        </motion.div>
        <motion.div variants={item}>
          <LiquidGlass className="liquidGlass-pro bg-gradient-to-br from-steel-200 to-steel-300 p-6">
            <span className="rounded-lg bg-navy-950 px-2 py-1 text-xs font-semibold text-white">Pro</span>
            <ul className="mt-4 space-y-2 text-sm text-navy-800/70">
              <li>✓ Unlimited team members</li>
              <li>✓ 1 TB storage</li>
              <li>✓ 4K videos</li>
            </ul>
            <button type="button" className="mt-5 w-full rounded-full bg-navy-950 py-2 text-sm text-white">Upgrade plan</button>
          </LiquidGlass>
        </motion.div>
      </motion.div>
    </div>
  );
}
