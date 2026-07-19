import { useTheme } from "./theme";
import { Button } from "./lib/watercolor";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const dark = theme === "dark";
  return (
    <Button
      buttonStyle="text"
      variant="secondary"
      fullWidth
      onClick={toggleTheme}
      className="!justify-start !text-[#103222] hover:!bg-[#e9e9ebb5] hover:!text-[#350180] !px-3 !rounded-xl"
    >
      <span className="inline-flex items-center gap-3">
        <svg
          className="h-[18px] w-[32px] shrink-0"
          viewBox="0 0 32 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect x="1" y="1" width="30" height="14" rx="7" stroke="currentColor" strokeWidth="2" />
          <circle cx={dark ? "24" : "8"} cy="8" r="3" stroke="currentColor" strokeWidth="2" />
        </svg>
        Dark Mode
      </span>
    </Button>
  );
}
