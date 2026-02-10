import { motion } from "framer-motion";

export function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`skeleton h-4 ${className}`} />;
}

export function SkeletonCard() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card p-5 space-y-3"
    >
      <SkeletonLine className="w-2/3 h-5" />
      <SkeletonLine className="w-1/2" />
      <SkeletonLine className="w-full h-24" />
      <div className="flex gap-2">
        <SkeletonLine className="w-16 h-7 rounded-full" />
        <SkeletonLine className="w-16 h-7 rounded-full" />
        <SkeletonLine className="w-16 h-7 rounded-full" />
      </div>
    </motion.div>
  );
}

export function SkeletonChart() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card p-5 space-y-3"
    >
      <SkeletonLine className="w-48 h-5" />
      <SkeletonLine className="w-full h-64" />
    </motion.div>
  );
}
