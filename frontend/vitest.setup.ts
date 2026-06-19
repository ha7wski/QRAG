// Global test setup. Runs before each test file.
import "@testing-library/jest-dom/vitest"; // adds DOM matchers (for component tests)
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup(); // unmount any React trees rendered by Testing Library
  localStorage.clear(); // each test starts from empty storage — no cross-test leakage
});
