import React from "react";

type SkeletonProps = {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "full";
};

const radiusClass: Record<NonNullable<SkeletonProps["rounded"]>, string> = {
  sm: "rounded",
  md: "rounded-md",
  lg: "rounded-xl",
  full: "rounded-full",
};

const Skeleton = ({ className = "", rounded = "md" }: SkeletonProps) => {
  return <div className={`ui-skeleton ${radiusClass[rounded]} ${className}`.trim()} aria-hidden="true" />;
};

export default Skeleton;
