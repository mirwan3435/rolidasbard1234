import { motion, type HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";

const LiquidGlass = ({ children, className = "", ...props }: HTMLMotionProps<"div"> & { children?: ReactNode }) => (
  <motion.div
    whileHover={{ y: -5 }}
    className={`liquidGlass-wrapper ${className}`}
    {...props}
  >
    <div className="liquidGlass-effect" />
    <div className="liquidGlass-content">{children}</div>
  </motion.div>
);

export default LiquidGlass;
